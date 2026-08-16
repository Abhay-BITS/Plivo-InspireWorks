"""The WebSocket feed replays history on connect and then streams new
events live. Uses starlette's synchronous TestClient because httpx's
ASGI transport does not speak WebSocket.
"""

from starlette.testclient import TestClient

from app.main import create_app


def test_connecting_after_events_replays_history():
    app = create_app()
    with TestClient(app) as test_client:
        test_client.post(
            "/voice/answer",
            data={"CallUUID": "ws-1", "To": "+917007745038", "From": "+918035454161"},
        )
        with test_client.websocket_connect("/ws/live") as ws:
            message = ws.receive_json()
            assert message["call_uuid"] == "ws-1"
            assert message["type"] == "xml_served"


def test_new_events_stream_live():
    app = create_app()
    with TestClient(app) as test_client:
        with test_client.websocket_connect("/ws/live") as ws:
            test_client.post(
                "/voice/answer",
                data={"CallUUID": "ws-2", "To": "+917007745038", "From": "+918035454161"},
            )
            message = ws.receive_json()
            assert message["call_uuid"] == "ws-2"
            assert message["type"] == "xml_served"
