"""
Streaming Job Application Agent with real-time monitoring support.

Extends JobApplicationAgent with:
- Screenshot capture after every tool execution
- Real-time event streaming via SSE
- Auto-pause on errors and before submission
- Tool-to-English conversion for human-readable updates
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from autoapply.services.llm.agents import JobApplicationAgent
from autoapply.services.llm.tools import BrowserTools
from autoapply.sse import SSEManager
from autoapply.services.db import Txc

logger = logging.getLogger(__name__)


class StreamingJobApplicationAgent(JobApplicationAgent):
    """
    Job Application Agent with real-time streaming capabilities.

    Captures screenshots after each tool execution and streams events
    to frontend via SSE for real-time monitoring.
    """

    def __init__(
        self,
        browser_tools: BrowserTools,
        sse_manager: SSEManager,
        session_id: str,
        screenshot_dir: str,
        model: str = "x-ai/grok-4.1-fast",
    ):
        """
        Initialize streaming agent.

        Args:
            browser_tools: BrowserTools instance with Playwright page
            sse_manager: SSEManager for streaming events
            session_id: Unique session identifier
            screenshot_dir: Directory to save screenshots
            model: OpenRouter model ID
        """
        super().__init__(browser_tools=browser_tools, model=model)

        self.sse_manager = sse_manager
        self.session_id = session_id
        self.screenshot_counter = 0
        self.screenshot_dir = screenshot_dir
        self.page = browser_tools.page

        # Create screenshot directory
        os.makedirs(self.screenshot_dir, exist_ok=True)

    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        """
        Override to add screenshot capture and event streaming.

        Workflow:
        1. Send tool_call event to frontend
        2. Update database with current step
        3. Execute the tool (parent class method)
        4. Capture screenshot
        5. Send screenshot event
        6. Check for pause triggers
        7. Return result
        """

        # Convert tool call to plain English
        description = self._tool_to_english(tool_name, arguments)

        # Send tool call event to frontend
        await self._send_event(
            {
                "type": "tool_call",
                "data": {
                    "tool": tool_name,
                    "description": description,
                    "step": f"Step {self.screenshot_counter + 1}: {description}",
                    "arguments": arguments,
                },
            }
        )

        # Update database with current step
        try:
            with Txc() as tx:
                tx.update_session_step(self.session_id, description)
        except Exception as e:
            logger.warning(f"Failed to update session step: {e}")

        # Execute tool (parent class method handles validation and execution)
        try:
            result = await super().execute_tool(tool_name, arguments)

            # Check if result contains an error
            if isinstance(result, dict) and "error" in result:
                # Tool execution failed - pause for user intervention
                await self._handle_error(tool_name, result["error"])
                return result

            # Capture screenshot after successful execution
            screenshot_url = await self._capture_screenshot(tool_name)

            # Send screenshot event
            await self._send_event(
                {
                    "type": "screenshot",
                    "data": {
                        "url": screenshot_url,
                        "step_number": self.screenshot_counter,
                        "tool": tool_name,
                    },
                }
            )

            # Check for auto-pause triggers
            await self._check_pause_triggers(tool_name, arguments, result)

            return result

        except Exception as e:
            # Execution exception - pause and notify
            await self._handle_error(tool_name, str(e))
            # Re-raise so parent class can handle it
            raise

    async def _capture_screenshot(self, tool_name: str) -> str:
        """
        Capture and save screenshot after tool execution.

        Args:
            tool_name: Name of the tool that was executed

        Returns:
            URL path to access the screenshot
        """
        self.screenshot_counter += 1
        filename = f"step_{self.screenshot_counter:03d}_{tool_name}.png"
        filepath = os.path.join(self.screenshot_dir, filename)

        try:
            # Capture screenshot from Playwright page
            screenshot_bytes = await self.page.screenshot(type="png", full_page=False)

            # Save to file
            with open(filepath, "wb") as f:
                f.write(screenshot_bytes)

            # Update latest.png symlink for quick card display
            latest_path = os.path.join(self.screenshot_dir, "latest.png")
            if os.path.exists(latest_path) or os.path.islink(latest_path):
                os.remove(latest_path)
            os.symlink(filename, latest_path)

            # Insert timeline event in database
            try:
                with Txc() as tx:
                    tx.insert_timeline_event(
                        session_id=self.session_id,
                        event_type="screenshot",
                        content=f"Screenshot captured after {tool_name}",
                        screenshot_path=filepath,
                    )
            except Exception as e:
                logger.warning(f"Failed to insert timeline event: {e}")

            # Return URL for frontend to fetch
            # Extract relative path from screenshot_dir
            # Format: /api/screenshots/{session_id}/{filename}
            return f"/api/screenshots/{self.session_id}/{filename}"

        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return ""

    async def _check_pause_triggers(self, tool_name: str, arguments: dict, result: Any):
        """
        Check if agent should auto-pause based on tool execution.

        Auto-pause triggers:
        - Before final application submission (browser_click on submit button)
        - Manual pause requested by user

        Args:
            tool_name: Name of executed tool
            arguments: Tool arguments
            result: Tool execution result
        """
        # Check if this is a submit button click
        if tool_name == "browser_click":
            element = arguments.get("element", "").lower()
            if any(
                keyword in element
                for keyword in ["submit", "apply", "send application"]
            ):
                await self._pause_for_review(
                    "Ready to submit application - paused for final review"
                )
                return

        # Check if manual pause was requested
        try:
            with Txc() as tx:
                session = tx.get_application_session(self.session_id)

            if session and session["status"] == "paused":
                await self._wait_for_resume()
        except Exception as e:
            logger.warning(f"Failed to check pause status: {e}")

    async def _handle_error(self, tool_name: str, error: str):
        """
        Handle errors by pausing agent and notifying user.

        Args:
            tool_name: Tool that failed
            error: Error message
        """
        error_msg = f"Error in {tool_name}: {error}"
        logger.error(error_msg)

        # Update session status to paused
        try:
            with Txc() as tx:
                tx.update_session_status(self.session_id, "paused", error=error_msg)
                tx.insert_timeline_event(
                    session_id=self.session_id,
                    event_type="error",
                    content=error_msg,
                    metadata={"tool": tool_name},
                )
        except Exception as e:
            logger.error(f"Failed to update session on error: {e}")

        # Send error event to frontend
        await self._send_event(
            {
                "type": "error",
                "data": {
                    "error": error_msg,
                    "tool": tool_name,
                },
            }
        )

        # Wait for user to resume
        await self._wait_for_resume()

    async def _pause_for_review(self, reason: str):
        """
        Pause agent for user review.

        Args:
            reason: Reason for pausing
        """
        logger.info(f"Pausing agent: {reason}")

        # Update session status
        try:
            with Txc() as tx:
                tx.update_session_status(self.session_id, "paused")
                tx.insert_timeline_event(
                    session_id=self.session_id,
                    event_type="pause",
                    content=reason,
                )
        except Exception as e:
            logger.error(f"Failed to update session on pause: {e}")

        # Send pause event
        await self._send_event({"type": "pause", "data": {"reason": reason}})

        # Wait for resume
        await self._wait_for_resume()

    async def _wait_for_resume(self):
        """
        Wait until user clicks resume button.
        Polls database every 2 seconds to check status.
        """
        logger.info(f"Waiting for resume signal for session {self.session_id}")

        while True:
            await asyncio.sleep(2)

            try:
                with Txc() as tx:
                    session = tx.get_application_session(self.session_id)

                if not session:
                    logger.error(f"Session {self.session_id} not found")
                    break

                if session["status"] == "running":
                    logger.info(f"Session {self.session_id} resumed")

                    # Send resume event
                    await self._send_event(
                        {"type": "resume", "data": {"message": "Agent resumed by user"}}
                    )

                    # Insert timeline event
                    try:
                        with Txc() as tx:
                            tx.insert_timeline_event(
                                session_id=self.session_id,
                                event_type="resume",
                                content="Agent resumed",
                            )
                    except Exception as e:
                        logger.warning(f"Failed to insert resume event: {e}")

                    break

            except Exception as e:
                logger.error(f"Error checking resume status: {e}")
                await asyncio.sleep(5)  # Longer delay on error

    def _tool_to_english(self, tool_name: str, args: dict) -> str:
        """
        Convert tool calls to plain English descriptions.

        Args:
            tool_name: Name of the tool
            args: Tool arguments

        Returns:
            Human-readable description
        """
        templates = {
            "browser_navigate": f"Navigating to {args.get('url', 'page')}",
            "browser_click": f"Clicking {args.get('element', 'element')}",
            "browser_type": f"Typing into {args.get('element', 'field')}",
            "browser_fill_form": f"Filling form with {len(args.get('fields', []))} fields",
            "browser_file_upload": "Uploading file",
            "browser_select_option": f"Selecting option in {args.get('element', 'dropdown')}",
            "browser_wait_for": "Waiting for page to load",
            "browser_snapshot": "Analyzing page content",
            "get_page_state": "Analyzing page structure",
            "browser_press_key": f"Pressing {args.get('key', 'key')}",
            "browser_hover": f"Hovering over {args.get('element', 'element')}",
            "browser_drag": "Dragging element",
            "browser_handle_dialog": "Handling dialog",
            "browser_evaluate": "Executing JavaScript",
            "browser_run_code": "Running custom browser code",
            "browser_take_screenshot": "Taking screenshot",
            "browser_console_messages": "Reading console messages",
            "browser_network_requests": "Analyzing network requests",
            "browser_resize": "Resizing browser window",
            "browser_tabs": "Managing browser tabs",
            "browser_navigate_back": "Going back to previous page",
        }

        return templates.get(tool_name, f"Executing {tool_name}")

    async def _send_event(self, event: dict):
        """
        Send event to SSE stream.

        Args:
            event: Event dict with 'type' and 'data' keys
        """
        event["session_id"] = self.session_id
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        await self.sse_manager.send_event(self.session_id, event)
