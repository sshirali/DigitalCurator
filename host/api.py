"""FastAPI application for Digital Curator MVP."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from host.data_manager import DataManager
from host.db.init import init_db
from host.decision_sync import DecisionSync
from host.indexer import Indexer
from host.models import Category, Decision
from host.scanner import Scanner
from host.trash_manager import TrashManager

# ---------------------------------------------------------------------------
# App and singletons
# ---------------------------------------------------------------------------

app = FastAPI(title="Digital Curator")

_indexer = Indexer()
_decision_sync = DecisionSync(indexer=_indexer)
_trash_manager = TrashManager(indexer=_indexer)
_data_manager = DataManager()
_scanner = Scanner(indexer=_indexer)

# scan_id -> progress float (0-100)
_scan_progress: dict[str, float] = {}


@app.on_event("startup")
def _startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    directory: str


class DecisionRequest(BaseModel):
    file_id: int
    decision: str  # "keep" | "delete"


class TrashRequest(BaseModel):
    file_ids: list[int]


class WipeRequest(BaseModel):
    confirm: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _file_record_to_dict(record: Any) -> dict:
    return {
        "id": record.id,
        "abs_path": str(record.abs_path),
        "thumb_path": str(record.thumb_path) if record.thumb_path else None,
        "file_size": record.file_size,
        "last_modified": record.last_modified,
        "sha256": record.sha256,
        "phash": record.phash,
        "thumb_status": record.thumb_status,
        "is_screenshot": record.is_screenshot,
        "screenshot_conf": record.screenshot_conf,
        "laplacian_var": record.laplacian_var,
        "mean_luminance": record.mean_luminance,
        "is_blurry": record.is_blurry,
        "is_dark": record.is_dark,
        "decision": record.decision,
        "status": record.status,
    }


def _member_to_dict(record: Any) -> dict:
    return {
        "id": record.id,
        "abs_path": str(record.abs_path),
        "thumb_path": str(record.thumb_path) if record.thumb_path else None,
        "width": None,
        "height": None,
        "laplacian_var": record.laplacian_var,
        "decision": record.decision,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/scan", status_code=202)
def post_scan(body: ScanRequest) -> dict:
    """Start a background scan and return a scan_id."""
    directory = Path(body.directory)
    if not directory.is_dir():
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid directory", "detail": str(directory)},
        )

    scan_id = str(uuid.uuid4())
    _scan_progress[scan_id] = 0.0

    def _progress_cb(pct: float) -> None:
        _scan_progress[scan_id] = pct

    async def _run() -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: _scanner.scan(directory, _progress_cb)
        )
        _scan_progress[scan_id] = 100.0

    asyncio.ensure_future(_run())
    return {"scan_id": scan_id, "status": "started"}


@app.get("/scan/progress")
def get_scan_progress(scan_id: str) -> StreamingResponse:
    """SSE stream of scan progress for a given scan_id."""

    async def _event_stream():
        while True:
            pct = _scan_progress.get(scan_id, 0.0)
            yield f"data: {pct:.1f}\n\n"
            if pct >= 100.0:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/triage/{category}")
def get_triage(category: str) -> list[dict]:
    """Return all files flagged for the given category."""
    try:
        cat = Category(category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid category",
                "detail": f"Must be one of: {[c.value for c in Category]}",
            },
        )
    try:
        records = _indexer.get_flagged(cat)
        return [_file_record_to_dict(r) for r in records]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "detail": str(exc)},
        )


@app.get("/groups/{group_id}")
def get_group(group_id: int) -> dict:
    """Return duplicate group detail with member metadata."""
    try:
        group = _indexer.get_group(group_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"error": "Group not found", "detail": f"id={group_id}"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "detail": str(exc)},
        )
    return {
        "id": group.id,
        "group_type": group.group_type,
        "winner_id": group.winner_id,
        "members": [_member_to_dict(m) for m in group.members],
    }


@app.get("/thumbs/{file_id}")
def get_thumb(file_id: int) -> FileResponse:
    """Serve thumbnail JPEG for a file."""
    record = _indexer.get_file_by_id(file_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "File not found", "detail": f"id={file_id}"},
        )
    if record.thumb_path is None or not Path(record.thumb_path).exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Thumbnail not found",
                "detail": f"id={file_id}",
            },
        )
    return FileResponse(str(record.thumb_path), media_type="image/jpeg")


@app.post("/decisions", status_code=200)
async def post_decision(body: DecisionRequest) -> dict:
    """Record a keep/delete decision for a file."""
    if body.decision not in ("keep", "delete"):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Invalid decision",
                "detail": "Must be 'keep' or 'delete'",
            },
        )
    record = _indexer.get_file_by_id(body.file_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "File not found",
                "detail": f"id={body.file_id}",
            },
        )
    try:
        await _decision_sync.record_decision(
            body.file_id, Decision(body.decision)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "detail": str(exc)},
        )
    return {"status": "ok"}


@app.get("/decisions")
def get_decisions() -> list[dict]:
    """Return all current keep/delete decisions."""
    try:
        payloads = _decision_sync.get_all_decisions()
        return [
            {
                "file_id": p.file_id,
                "decision": p.decision,
                "timestamp": p.timestamp,
            }
            for p in payloads
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "detail": str(exc)},
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time decision sync."""
    await websocket.accept()
    await _decision_sync.connect(websocket)
    try:
        # Send full decision state on connect
        payloads = _decision_sync.get_all_decisions()
        import json
        import dataclasses
        state = [dataclasses.asdict(p) for p in payloads]
        await websocket.send_text(json.dumps(state))

        # Relay incoming messages
        while True:
            data = await websocket.receive_text()
            try:
                from host.models import DecisionPayload
                msg = json.loads(data)
                payload = DecisionPayload(
                    file_id=msg["file_id"],
                    decision=msg["decision"],
                    timestamp=msg.get("timestamp", 0.0),
                )
                await _decision_sync.handle_remote_decision(payload)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "Malformed WS payload: %s", exc
                )
                await websocket.send_text(
                    json.dumps({"error": str(exc)})
                )
    except WebSocketDisconnect:
        pass
    finally:
        _decision_sync.disconnect(websocket)


@app.post("/trash")
def post_trash(body: TrashRequest) -> dict:
    """Move files to OS Trash."""
    try:
        result = _trash_manager.trash_files(body.file_ids)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "detail": str(exc)},
        )
    return {
        "trashed": result.trashed,
        "failed": [
            {
                "file_id": f.file_id,
                "abs_path": str(f.abs_path),
                "error": f.error,
            }
            for f in result.failed
        ],
    }


@app.post("/wipe")
def post_wipe(body: WipeRequest) -> dict:
    """Wipe all app data (DB + thumbnail cache)."""
    if body.confirm != "WIPE":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Confirmation required",
                "detail": "Send {\"confirm\": \"WIPE\"} to proceed",
            },
        )
    try:
        _data_manager.wipe()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "Wipe failed", "detail": str(exc)},
        )
    return {"status": "wiped"}
