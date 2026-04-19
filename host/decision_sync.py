"""DecisionSync: manages WebSocket connections and broadcasts Keep/Delete decisions."""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import time
from typing import TYPE_CHECKING

from host.models import Decision, DecisionPayload

if TYPE_CHECKING:
    from host.indexer import Indexer

logger = logging.getLogger(__name__)


class DecisionSync:
    """Manages the WebSocket connection pool and broadcasts state changes."""

    def __init__(self, indexer: "Indexer | None" = None) -> None:
        if indexer is None:
            from host.indexer import Indexer as _Indexer
            indexer = _Indexer()
        self._indexer = indexer
        self._connections: set = set()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self, websocket) -> None:
        """Add a WebSocket client to the connection pool."""
        self._connections.add(websocket)

    def disconnect(self, websocket) -> None:
        """Remove a WebSocket client from the connection pool."""
        self._connections.discard(websocket)

    # ------------------------------------------------------------------
    # Decision recording and broadcasting
    # ------------------------------------------------------------------

    async def record_decision(self, file_id: int, decision: Decision) -> None:
        """Persist decision to DB and broadcast to all connected clients."""
        self._indexer.set_decision(file_id, decision)
        decision_str = decision.value if isinstance(decision, Decision) else str(decision)
        payload = DecisionPayload(
            file_id=file_id,
            decision=decision_str,
            timestamp=time.time(),
        )
        await self.broadcast(payload)

    async def broadcast(self, payload: DecisionPayload) -> None:
        """Send JSON payload to all connected WebSocket clients concurrently."""
        if not self._connections:
            return

        data = json.dumps(dataclasses.asdict(payload))

        async def _send(ws):
            try:
                await ws.send_text(data)
            except Exception:
                logger.debug("Client disconnected during broadcast; removing from pool.")
                self._connections.discard(ws)

        await asyncio.gather(*[_send(ws) for ws in list(self._connections)], return_exceptions=True)

    # ------------------------------------------------------------------
    # Remote decision handling
    # ------------------------------------------------------------------

    async def handle_remote_decision(self, payload: DecisionPayload) -> None:
        """Validate and apply a decision received from a Remote UI client."""
        if not isinstance(payload.file_id, int):
            logger.warning("Invalid decision payload: file_id must be int, got %r", payload.file_id)
            raise ValueError(f"Invalid file_id: {payload.file_id!r}")

        if payload.decision not in ("keep", "delete"):
            logger.warning("Invalid decision payload: decision must be 'keep' or 'delete', got %r", payload.decision)
            raise ValueError(f"Invalid decision value: {payload.decision!r}")

        decision = Decision(payload.decision)
        await self.record_decision(payload.file_id, decision)

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_all_decisions(self) -> list[DecisionPayload]:
        """Return all files that have a Keep or Delete decision."""
        from host.db.init import get_session
        from host.db.schema import FileModel

        session = get_session()
        try:
            rows = (
                session.query(FileModel)
                .filter(FileModel.decision != "undecided")
                .all()
            )
            return [
                DecisionPayload(
                    file_id=row.id,
                    decision=row.decision,
                    timestamp=time.time(),
                )
                for row in rows
            ]
        finally:
            session.close()
