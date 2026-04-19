"""Unit tests for DecisionSync."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from host.decision_sync import DecisionSync
from host.models import Decision, DecisionPayload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sync(indexer=None) -> DecisionSync:
    if indexer is None:
        indexer = MagicMock()
    return DecisionSync(indexer=indexer)


class _FakeWebSocket:
    """Minimal WebSocket stand-in that records sent messages."""

    def __init__(self, fail: bool = False):
        self.messages: list[str] = []
        self.fail = fail

    async def send_text(self, data: str) -> None:
        if self.fail:
            raise RuntimeError("disconnected")
        self.messages.append(data)


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------

def test_connect_adds_to_pool():
    sync = _make_sync()
    ws = _FakeWebSocket()
    asyncio.get_event_loop().run_until_complete(sync.connect(ws))
    assert ws in sync._connections


def test_disconnect_removes_from_pool():
    sync = _make_sync()
    ws = _FakeWebSocket()
    asyncio.get_event_loop().run_until_complete(sync.connect(ws))
    sync.disconnect(ws)
    assert ws not in sync._connections


def test_disconnect_unknown_is_noop():
    sync = _make_sync()
    ws = _FakeWebSocket()
    # Should not raise even if ws was never added
    sync.disconnect(ws)


# ---------------------------------------------------------------------------
# record_decision
# ---------------------------------------------------------------------------

def test_record_decision_persists_to_db():
    indexer = MagicMock()
    sync = _make_sync(indexer)
    asyncio.get_event_loop().run_until_complete(
        sync.record_decision(1, Decision.keep)
    )
    indexer.set_decision.assert_called_once_with(1, Decision.keep)


def test_record_decision_broadcasts_payload():
    indexer = MagicMock()
    sync = _make_sync(indexer)
    ws = _FakeWebSocket()
    asyncio.get_event_loop().run_until_complete(sync.connect(ws))
    asyncio.get_event_loop().run_until_complete(
        sync.record_decision(42, Decision.delete)
    )
    assert len(ws.messages) == 1
    import json
    payload = json.loads(ws.messages[0])
    assert payload["file_id"] == 42
    assert payload["decision"] == "delete"
    assert "timestamp" in payload


# ---------------------------------------------------------------------------
# broadcast
# ---------------------------------------------------------------------------

def test_broadcast_sends_to_all_clients():
    sync = _make_sync()
    ws1, ws2 = _FakeWebSocket(), _FakeWebSocket()
    asyncio.get_event_loop().run_until_complete(sync.connect(ws1))
    asyncio.get_event_loop().run_until_complete(sync.connect(ws2))
    payload = DecisionPayload(file_id=7, decision="keep", timestamp=1.0)
    asyncio.get_event_loop().run_until_complete(sync.broadcast(payload))
    assert len(ws1.messages) == 1
    assert len(ws2.messages) == 1


def test_broadcast_removes_failed_client():
    sync = _make_sync()
    good = _FakeWebSocket()
    bad = _FakeWebSocket(fail=True)
    asyncio.get_event_loop().run_until_complete(sync.connect(good))
    asyncio.get_event_loop().run_until_complete(sync.connect(bad))
    payload = DecisionPayload(file_id=3, decision="delete", timestamp=2.0)
    asyncio.get_event_loop().run_until_complete(sync.broadcast(payload))
    assert bad not in sync._connections
    assert good in sync._connections
    assert len(good.messages) == 1


def test_broadcast_no_connections_is_noop():
    sync = _make_sync()
    payload = DecisionPayload(file_id=1, decision="keep", timestamp=0.0)
    # Should not raise
    asyncio.get_event_loop().run_until_complete(sync.broadcast(payload))


# ---------------------------------------------------------------------------
# handle_remote_decision
# ---------------------------------------------------------------------------

def test_handle_remote_decision_valid_keep():
    indexer = MagicMock()
    sync = _make_sync(indexer)
    payload = DecisionPayload(file_id=5, decision="keep", timestamp=0.0)
    asyncio.get_event_loop().run_until_complete(
        sync.handle_remote_decision(payload)
    )
    indexer.set_decision.assert_called_once_with(5, Decision.keep)


def test_handle_remote_decision_valid_delete():
    indexer = MagicMock()
    sync = _make_sync(indexer)
    payload = DecisionPayload(file_id=9, decision="delete", timestamp=0.0)
    asyncio.get_event_loop().run_until_complete(
        sync.handle_remote_decision(payload)
    )
    indexer.set_decision.assert_called_once_with(9, Decision.delete)


def test_handle_remote_decision_invalid_decision_raises():
    sync = _make_sync()
    payload = DecisionPayload(file_id=1, decision="undecided", timestamp=0.0)
    with pytest.raises(ValueError):
        asyncio.get_event_loop().run_until_complete(
            sync.handle_remote_decision(payload)
        )


def test_handle_remote_decision_invalid_file_id_raises():
    sync = _make_sync()
    payload = DecisionPayload(file_id="not-an-int", decision="keep", timestamp=0.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        asyncio.get_event_loop().run_until_complete(
            sync.handle_remote_decision(payload)
        )


# ---------------------------------------------------------------------------
# get_all_decisions
# ---------------------------------------------------------------------------

def test_get_all_decisions_returns_decided_files():
    """get_all_decisions queries DB for non-undecided files."""
    sync = _make_sync()

    keep_row = MagicMock()
    keep_row.id = 1
    keep_row.decision = "keep"

    delete_row = MagicMock()
    delete_row.id = 2
    delete_row.decision = "delete"

    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.all.return_value = [
        keep_row, delete_row
    ]

    import sys
    import types

    # Mock both schema and init modules to avoid SQLAlchemy import issues
    fake_schema = types.ModuleType("host.db.schema")
    fake_schema.FileModel = MagicMock()

    fake_db_init = types.ModuleType("host.db.init")
    fake_db_init.get_session = MagicMock(return_value=mock_session)

    with patch.dict(sys.modules, {
        "host.db.schema": fake_schema,
        "host.db.init": fake_db_init,
    }):
        results = sync.get_all_decisions()

    assert len(results) == 2
    assert all(isinstance(r, DecisionPayload) for r in results)
    decisions = {r.file_id: r.decision for r in results}
    assert decisions[1] == "keep"
    assert decisions[2] == "delete"
