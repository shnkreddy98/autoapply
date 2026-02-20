import asyncio
import logging
import json
import httpx

from typing import Dict, List, Any, Callable, Optional, Type
from pydantic import BaseModel

from autoapply.env import MODEL, OPENROUTER_API_KEY
from autoapply.logging import get_logger

get_logger()
logger = logging.getLogger(__name__)


class AgentResult(BaseModel):
    """Result from agent execution"""

    output: Any = None
    usage: Dict[str, int] = {}
    iterations: int = 0
    success: bool = True
    error: Optional[str] = None


class Agent:
    """
    Base Agent class for OpenRouter LLM interactions.

    Supports:
    - Tool calling (function calling)
    - Structured output (JSON schema validation)
    - Conversation management
    - Retry logic with exponential backoff
    - Multi-turn interactions
    """

    def __init__(
        self,
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_functions: Optional[Dict[str, Callable]] = None,
        response_format: Optional[Type[BaseModel]] = None,
        model: str = MODEL,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tool_schemas: Optional[Dict[str, Type[BaseModel]]] = None,
    ):
        """
        Initialize agent.

        Args:
            system_prompt: System prompt defining agent behavior
            tools: List of tool schemas (OpenAI function calling format)
            tool_functions: Dict mapping tool names to async functions
            response_format: Pydantic model for structured JSON output
            model: OpenRouter model ID
            temperature: LLM temperature (0-1)
            max_tokens: Maximum tokens to generate
            tool_schemas: Dict mapping tool names to their Pydantic arg models (for validation)
        """
        if not OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. Get a key at https://openrouter.ai/keys"
            )

        self.system_prompt = system_prompt
        self.tools = tools or []
        self.tool_functions = tool_functions or {}
        self.tool_schemas = tool_schemas or {}  # Store Pydantic models for validation
        self.response_format = response_format
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        self.messages: List[Dict[str, Any]] = []
        self.result = AgentResult()
        self.running = False
        self.stop_requested = False

    def init_messages(self):
        """Initialize conversation with system prompt"""
        # Build system message
        system_content = self.system_prompt

        # If response_format is set, add schema to system prompt
        if self.response_format:
            schema = self.response_format.model_json_schema()
            # Clean up schema
            if "title" in schema:
                del schema["title"]
            if "properties" in schema:
                for prop in schema["properties"].values():
                    if "title" in prop:
                        del prop["title"]

            system_content += f"\n\nYou must respond with valid JSON matching this exact schema:\n{json.dumps(schema, indent=2)}\n\nReturn only the JSON object, no additional text."

        self.messages = [{"role": "system", "content": system_content}]

    async def _call_llm_with_retry(
        self, payload: dict, max_retries: int = 3
    ) -> Optional[httpx.Response]:
        """
        Call OpenRouter API with exponential backoff retry.

        Args:
            payload: Request payload
            max_retries: Maximum number of retry attempts

        Returns:
            Response object or None on failure
        """
        initial_delay = 2.0

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        self.url, headers=self.headers, json=payload
                    )

                    if response.status_code == 200:
                        return response
                    elif response.status_code >= 500:
                        logger.warning(
                            f"Server error {response.status_code}, "
                            f"retrying (attempt {attempt + 1}/{max_retries})..."
                        )
                    else:
                        # Client error - don't retry
                        logger.error(
                            f"API error {response.status_code}: {response.text}"
                        )
                        return None

            except (httpx.ReadError, httpx.ConnectError, httpx.ReadTimeout) as e:
                logger.warning(
                    f"Network error {type(e).__name__}, "
                    f"retrying (attempt {attempt + 1}/{max_retries})..."
                )
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return None

            # Exponential backoff
            if attempt < max_retries - 1:
                delay = initial_delay * (2**attempt)
                await asyncio.sleep(delay)

        logger.error("All retry attempts failed")
        return None

    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        """
        Execute a tool and return its result.

        Validates arguments against Pydantic schema if available,
        converts dict to Pydantic model, and passes validation errors
        back to the LLM for self-correction.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments (dict from LLM)

        Returns:
            Tool execution result or validation error
        """
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")

        # Check if tool exists
        if tool_name not in self.tool_functions:
            return {
                "error": f"Tool '{tool_name}' not found",
                "available_tools": list(self.tool_functions.keys()),
            }

        # Validate and convert arguments if Pydantic schema is available
        if tool_name in self.tool_schemas:
            schema_class = self.tool_schemas[tool_name]
            try:
                # Validate and convert dict to Pydantic model
                validated_args = schema_class(**arguments)
                logger.debug(f"Arguments validated successfully for {tool_name}")
            except Exception as e:
                # Return simple validation error to LLM so it can correct itself
                # Keep it simple to avoid "Thought signature" errors with Gemini
                error_msg = f"Validation error for '{tool_name}': {str(e)}\n\nPlease check the tool schema and try again with correct argument names and types."
                logger.warning(f"Validation failed for {tool_name}: {str(e)}")
                return {"error": error_msg}
        else:
            # No schema available, pass dict as-is
            validated_args = arguments
            logger.debug(f"No schema for {tool_name}, passing dict directly")

        # Execute the tool
        try:
            tool_func = self.tool_functions[tool_name]
            result = await tool_func(validated_args)
            return result
        except Exception as e:
            # Return execution error with details
            logger.error(f"Error executing {tool_name}: {str(e)}", exc_info=True)
            return {
                "error": f"Tool execution failed: {str(e)}",
                "tool": tool_name,
                "type": type(e).__name__,
            }

    async def run(self, query: str, max_iterations: int = 50) -> AgentResult:
        """
        Main agent execution loop.

        Args:
            query: User query/task
            max_iterations: Maximum number of LLM calls

        Returns:
            AgentResult with output and metadata
        """
        self.stop_requested = False
        self.running = True
        self.result = AgentResult()

        # Initialize messages if needed
        if not self.messages:
            self.init_messages()

        # Add user query
        self.messages.append({"role": "user", "content": query})

        for iteration in range(max_iterations):
            if self.stop_requested:
                logger.info("Agent stopped by user request")
                self.running = False
                self.result.success = False
                self.result.error = "Stopped by user"
                return self.result

            logger.info(f"Iteration {iteration + 1}/{max_iterations}")
            self.result.iterations = iteration + 1
            logger.debug(f"Messages in conversation: {len(self.messages)}")

            # Prepare payload
            payload = {
                "model": self.model,
                "messages": self.messages,
                "temperature": self.temperature,
            }
            logger.debug(
                f"Payload model: {self.model}, tools: {len(self.tools) if self.tools else 0}, response_format: {bool(self.response_format)}"
            )

            if self.max_tokens:
                payload["max_tokens"] = self.max_tokens

            # Add tools if available
            if self.tools:
                payload["tools"] = self.tools
                payload["tool_choice"] = "auto"

            # Add response format for structured output (with or without tools)
            if self.response_format:
                payload["response_format"] = {"type": "json_object"}

            # Make API call with retry logic
            response = await self._call_llm_with_retry(payload)

            if not response:
                self.running = False
                self.result.success = False
                self.result.error = "API call failed"
                return self.result

            # Parse response
            result = response.json()
            message = result.get("choices", [{}])[0].get("message", {})
            output = message.get("content", "")
            tool_calls = message.get("tool_calls", [])

            logger.debug(
                f"Response - output length: {len(output) if output else 0}, tool_calls: {len(tool_calls)}"
            )
            if output:
                logger.debug(
                    f"Output preview: {output[:200] if len(output) > 200 else output}"
                )

            # Track usage
            self.result.usage = result.get("usage", {})
            logger.debug(
                f"Token usage - input: {self.result.usage.get('prompt_tokens', 0)}, output: {self.result.usage.get('completion_tokens', 0)}"
            )

            # Add assistant message to history
            self.messages.append(message)

            # If no tool calls, we're done
            if not tool_calls:
                logger.debug("No tool calls in response - finalizing output")
                # Parse structured output if needed
                if self.response_format:
                    logger.debug(
                        f"Parsing structured output with format: {self.response_format.__name__}"
                    )
                    try:
                        logger.debug(
                            f"Raw output to parse: {output[:300] if len(output) > 300 else output}"
                        )

                        parsed_output = output.strip()

                        # Try to extract JSON from markdown code blocks or standalone JSON
                        if "```json" in parsed_output or "```" in parsed_output:
                            # Find JSON in markdown code blocks
                            start_idx = parsed_output.find("{")
                            end_idx = parsed_output.rfind("}") + 1
                            if start_idx != -1 and end_idx > start_idx:
                                parsed_output = parsed_output[start_idx:end_idx]
                                logger.debug(
                                    f"Extracted JSON from markdown: {parsed_output[:200]}"
                                )
                        elif not parsed_output.startswith("{"):
                            # If output doesn't start with {, try to find JSON object
                            start_idx = parsed_output.find("{")
                            end_idx = parsed_output.rfind("}") + 1
                            if start_idx != -1 and end_idx > start_idx:
                                parsed_output = parsed_output[start_idx:end_idx]
                                logger.debug(
                                    f"Extracted JSON from text: {parsed_output[:200]}"
                                )

                        data = json.loads(parsed_output)
                        logger.debug(
                            f"Parsed JSON keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}"
                        )
                        self.result.output = self.response_format(**data)
                        logger.info(
                            f"Successfully parsed {self.response_format.__name__} object"
                        )
                    except Exception as e:
                        self.running = True
                        self.messages.append(
                            {
                                "role": "user",
                                "content": f"Failed to parse structured output: {e}",
                            }
                        )
                        continue
                        # logger.error(f"Failed to parse structured output: {e}")
                        # logger.error(
                        #     f"Output was: {output[:500] if output else 'empty'}"
                        # )
                        # self.result.success = False
                        # self.result.error = f"Invalid JSON output: {str(e)}"
                        # self.result.output = output
                else:
                    logger.debug("No response_format specified, returning raw output")
                    self.result.output = output

                self.running = False
                return self.result

            # Execute tool calls
            logger.debug(f"Processing {len(tool_calls)} tool calls")
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call["function"]["name"]
                tool_id = tool_call["id"]
                tool_args_raw = tool_call["function"]["arguments"]

                logger.debug(f"Tool call {i + 1}/{len(tool_calls)}: {tool_name}")
                logger.debug(
                    f"Tool args: {tool_args_raw[:200] if isinstance(tool_args_raw, str) and len(tool_args_raw) > 200 else tool_args_raw}"
                )

                # Parse arguments
                try:
                    if isinstance(tool_args_raw, str):
                        tool_args = (
                            json.loads(tool_args_raw) if tool_args_raw.strip() else {}
                        )
                    else:
                        tool_args = tool_args_raw
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool arguments: {e}")
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": json.dumps({"error": f"Invalid JSON: {str(e)}"}),
                        }
                    )
                    continue

                # Execute tool
                logger.debug(f"Executing tool: {tool_name}")
                tool_result = await self.execute_tool(tool_name, tool_args)
                logger.debug(
                    f"Tool result: {str(tool_result)[:200] if tool_result else 'None'}"
                )

                # Add tool result to conversation
                # Handle dict vs string results
                if isinstance(tool_result, dict):
                    content = json.dumps(tool_result)
                elif isinstance(tool_result, str):
                    content = tool_result
                else:
                    content = str(tool_result)

                self.messages.append(
                    {"role": "tool", "tool_call_id": tool_id, "content": content}
                )

        # Max iterations reached - try to parse final output if we have structured format
        logger.warning(f"Max iterations ({max_iterations}) reached")
        self.running = False

        # Get the last assistant message if available
        last_message = None
        for msg in reversed(self.messages):
            if msg.get("role") == "assistant":
                last_message = msg
                break

        if last_message and self.response_format:
            output = last_message.get("content", "")
            if output:
                try:
                    logger.debug(f"Attempting to parse final output: {output[:200]}")

                    parsed_output = output.strip()

                    # Try to extract JSON from markdown code blocks or standalone JSON
                    if "```json" in parsed_output or "```" in parsed_output:
                        start_idx = parsed_output.find("{")
                        end_idx = parsed_output.rfind("}") + 1
                        if start_idx != -1 and end_idx > start_idx:
                            parsed_output = parsed_output[start_idx:end_idx]
                            logger.debug("Extracted JSON from markdown in final output")
                    elif not parsed_output.startswith("{"):
                        start_idx = parsed_output.find("{")
                        end_idx = parsed_output.rfind("}") + 1
                        if start_idx != -1 and end_idx > start_idx:
                            parsed_output = parsed_output[start_idx:end_idx]
                            logger.debug("Extracted JSON from text in final output")

                    data = json.loads(parsed_output)
                    self.result.output = self.response_format(**data)
                    self.result.success = True
                    self.result.error = None
                    logger.info(
                        "Successfully parsed final structured output after max iterations"
                    )
                    return self.result
                except Exception as e:
                    logger.error(f"Failed to parse final output: {e}")

        self.result.success = False
        self.result.error = "Max iterations reached without valid output"
        return self.result

    def stop(self):
        """Request agent to stop"""
        self.stop_requested = True
