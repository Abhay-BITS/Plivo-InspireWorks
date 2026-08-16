"""The live event feed. On connect the socket first receives up to the
last fifty events for every currently active call, so a browser opening
mid call sees the flow so far instead of a blank panel, then every new
CallEvent as it is published.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.calls.service import CallService
from app.observability.logging import get_logger

router = APIRouter(tags=["ws"])
logger = get_logger(__name__)


@router.websocket("/ws/live")
async def live(websocket: WebSocket) -> None:
    await websocket.accept()
    service: CallService = websocket.app.state.service
    bus = websocket.app.state.bus
    queue = bus.subscribe()

    try:
        for session in await service.active_calls():
            for event in service.history(session.call_uuid):
                await websocket.send_json(event.to_json())

        while True:
            event = await queue.get()
            await websocket.send_json(event.to_json())
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(queue)
