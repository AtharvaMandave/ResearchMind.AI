"""
ResearchMind AI – WebSocket Endpoint
Provides real-time agent status updates to connected frontend clients.
"""
import asyncio
import logging
from collections import defaultdict
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas import AgentStatusEvent

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])

# ── Connection Manager ────────────────────────────────────────────────────────
# Maps project_id → set of connected WebSocket clients
_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
# Maps project_id → asyncio.Queue for broadcasting events
_queues: Dict[str, asyncio.Queue] = {}


class ConnectionManager:
    """Manages WebSocket connections per project."""

    @staticmethod
    async def connect(project_id: str, websocket: WebSocket):
        await websocket.accept()
        _connections[project_id].add(websocket)
        logger.info("[WS] Client connected for project %s (total: %d)",
                     project_id, len(_connections[project_id]))

    @staticmethod
    def disconnect(project_id: str, websocket: WebSocket):
        _connections[project_id].discard(websocket)
        if not _connections[project_id]:
            del _connections[project_id]
        logger.info("[WS] Client disconnected for project %s", project_id)

    @staticmethod
    async def broadcast(project_id: str, event: AgentStatusEvent):
        """Send an event to all connected clients for a given project."""
        dead = set()
        for ws in _connections.get(project_id, set()):
            try:
                await ws.send_json(event.model_dump())
            except Exception:
                dead.add(ws)
        # Clean up dead connections
        for ws in dead:
            _connections[project_id].discard(ws)


manager = ConnectionManager()


async def emit_agent_event(
    project_id: str,
    agent: str,
    status: str,
    message: str | None = None,
    data: dict | None = None,
):
    """
    Convenience function to emit agent status events.
    Called from within agent nodes or the pipeline coordinator.
    Updates the database project status when an agent starts.
    """
    event = AgentStatusEvent(
        project_id=project_id,
        agent=agent,
        status=status,
        message=message,
        data=data,
    )
    await manager.broadcast(project_id, event)
    logger.info("[WS] Event: project=%s agent=%s status=%s", project_id, agent, status)

    # Automatically update project status in DB when an agent node starts
    status_map = {
        "planner": "planning",
        "researcher": "researching",
        "critic": "critiquing",
        "writer": "writing",
        "reviewer": "reviewing",
    }

    if status == "started" and agent in status_map:
        from app.database import AsyncSessionLocal
        from app.models import Project
        import uuid
        try:
            async with AsyncSessionLocal() as session:
                project = await session.get(Project, uuid.UUID(project_id))
                if project:
                    project.status = status_map[agent]
                    await session.commit()
                    logger.info("[WS] Updated DB project %s status to '%s'", project_id, status_map[agent])
        except Exception as exc:
            logger.warning("[WS] Failed to update DB project status for project %s: %s", project_id, exc)


# ── WebSocket Route ──────────────────────────────────────────────────────────
@router.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time agent status updates.
    Connect to: ws://localhost:8000/api/v1/ws/{project_id}
    """
    print(f"⚡⚡⚡ [WS Endpoint] Incoming connection request for project_id: '{project_id}' ⚡⚡⚡")
    await manager.connect(project_id, websocket)
    try:
        # Keep connection alive — listen for client messages (e.g., pings)
        while True:
            data = await websocket.receive_text()
            # Echo pong for keepalive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)
    except Exception:
        manager.disconnect(project_id, websocket)
