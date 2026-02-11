import asyncio
import logging
import json
import httpx

from datetime import datetime
from typing import Dict, List, Any, Callable, Union, Optional, Type
from pydantic import BaseModel

from autoapply.env import OPENROUTER_API_KEY
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
        model: str = "google/gemini-2.0-flash-exp:free",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
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
        """
        if not OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. "
                "Get a key at https://openrouter.ai/keys"
            )

        self.system_prompt = system_prompt
        self.tools = tools or []
        self.tool_functions = tool_functions or {}
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

    def _prune_history(self, max_messages: int = 20):
        """
        Prune conversation to stay within context limits.
        Keep: System message + recent messages
        """
        if len(self.messages) > max_messages:
            system_msg = self.messages[0]
            recent_messages = self.messages[-(max_messages - 1):]
            self.messages = [system_msg] + recent_messages
            logger.debug(f"Pruned conversation history to {len(self.messages)} messages")

    async def _call_llm_with_retry(
        self,
        payload: dict,
        max_retries: int = 3
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
                        self.url,
                        headers=self.headers,
                        json=payload
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
                        logger.error(f"API error {response.status_code}: {response.text}")
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
                delay = initial_delay * (2 ** attempt)
                await asyncio.sleep(delay)

        logger.error("All retry attempts failed")
        return None

    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        """
        Execute a tool and return its result.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")

        if tool_name not in self.tool_functions:
            return {
                "error": f"Tool '{tool_name}' not found",
                "available_tools": list(self.tool_functions.keys())
            }

        try:
            tool_func = self.tool_functions[tool_name]

            # If the tool function expects a Pydantic model, construct it
            # Otherwise, pass the dict directly
            result = await tool_func(arguments)
            return result
        except Exception as e:
            logger.error(f"Error executing {tool_name}: {str(e)}", exc_info=True)
            return {"error": str(e), "type": type(e).__name__}

    async def run(
        self,
        query: str,
        max_iterations: int = 50
    ) -> AgentResult:
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

            # Prune history to manage context size
            self._prune_history()

            # Prepare payload
            payload = {
                "model": self.model,
                "messages": self.messages,
                "temperature": self.temperature,
            }

            if self.max_tokens:
                payload["max_tokens"] = self.max_tokens

            # Add tools if available
            if self.tools:
                payload["tools"] = self.tools
                payload["tool_choice"] = "auto"

            # Add response format for structured output (without tools)
            if self.response_format and not self.tools:
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

            # Track usage
            self.result.usage = result.get("usage", {})

            # Add assistant message to history
            self.messages.append(message)

            # If no tool calls, we're done
            if not tool_calls:
                # Parse structured output if needed
                if self.response_format:
                    try:
                        data = json.loads(output)
                        self.result.output = self.response_format(**data)
                    except Exception as e:
                        logger.error(f"Failed to parse structured output: {e}")
                        self.result.success = False
                        self.result.error = f"Invalid JSON output: {str(e)}"
                        self.result.output = output
                else:
                    self.result.output = output

                self.running = False
                return self.result

            # Execute tool calls
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_id = tool_call["id"]
                tool_args_raw = tool_call["function"]["arguments"]

                # Parse arguments
                try:
                    if isinstance(tool_args_raw, str):
                        tool_args = json.loads(tool_args_raw) if tool_args_raw.strip() else {}
                    else:
                        tool_args = tool_args_raw
                except json.JSONDecodeError as e:
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": json.dumps({"error": f"Invalid JSON: {str(e)}"})
                    })
                    continue

                # Execute tool
                tool_result = await self.execute_tool(tool_name, tool_args)

                # Add tool result to conversation
                # Handle dict vs string results
                if isinstance(tool_result, dict):
                    content = json.dumps(tool_result)
                elif isinstance(tool_result, str):
                    content = tool_result
                else:
                    content = str(tool_result)

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": content
                })

        # Max iterations reached
        logger.warning(f"Max iterations ({max_iterations}) reached")
        self.running = False
        self.result.success = False
        self.result.error = "Max iterations reached"
        return self.result

    def stop(self):
        """Request agent to stop"""
        self.stop_requested = True
