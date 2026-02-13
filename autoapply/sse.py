"""
Server-Sent Events (SSE) Manager for real-time streaming to frontend.
"""

import asyncio
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class SSEManager:
    """Manages Server-Sent Event streams for real-time job application monitoring."""

    def __init__(self):
        self.active_streams: Dict[str, asyncio.Queue] = {}

    async def add_stream(self, session_id: str) -> asyncio.Queue:
        """
        Register new SSE stream for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            asyncio.Queue for sending events to this stream
        """
        queue = asyncio.Queue()
        self.active_streams[session_id] = queue
        logger.info(f"SSE stream added for session {session_id}")
        return queue

    async def remove_stream(self, session_id: str):
        """
        Remove SSE stream for a session.

        Args:
            session_id: Session identifier to remove
        """
        if session_id in self.active_streams:
            # Send end signal (None) to close the stream gracefully
            try:
                await self.active_streams[session_id].put(None)
            except:
                pass
            del self.active_streams[session_id]
            logger.info(f"SSE stream removed for session {session_id}")

    async def send_event(self, session_id: str, event: dict):
        """
        Send event to specific session stream.

        Args:
            session_id: Target session identifier
            event: Event data dict with 'type' and 'data' keys
        """
        if session_id in self.active_streams:
            try:
                await self.active_streams[session_id].put(event)
                logger.debug(f"Event sent to session {session_id}: {event.get('type')}")
            except Exception as e:
                logger.error(f"Error sending event to session {session_id}: {e}")
        else:
            logger.warning(f"No active stream for session {session_id}")

    def has_stream(self, session_id: str) -> bool:
        """
        Check if session has an active stream.

        Args:
            session_id: Session identifier to check

        Returns:
            True if stream exists, False otherwise
        """
        return session_id in self.active_streams
