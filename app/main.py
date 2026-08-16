"""App factory: builds settings, the shared singletons, mounts routers
and static files, and installs the exception handler that keeps a
crashing voice route from dropping the caller into silence.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.api.deps import get_settings as get_settings_dep
from app.api.routes_calls import router as calls_router
from app.api.routes_events import router as events_router
from app.api.routes_voice import router as voice_router
from app.api.routes_ws import router as ws_router
from app.calls.service import CallService, EventBus
from app.calls.store import InMemoryCallStateStore
from app.config import Settings, get_settings
from app.observability.logging import configure_logging, get_logger
from app.observability.timeline import Timeline
from app.telephony.client import PlivoClient
from app.telephony.xml_builder import error_document
from app.urls import CallbackUrls

logger = get_logger(__name__)

VOICE_PREFIXES = ("/voice", "/events")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    urls = CallbackUrls(settings)
    store = InMemoryCallStateStore(ttl_minutes=settings.session_ttl_minutes)
    timeline = Timeline()
    bus = EventBus()
    service = CallService(store=store, timeline=timeline, bus=bus, settings=settings, urls=urls)
    plivo_client = PlivoClient(settings, urls)

    app.state.settings = settings
    app.state.urls = urls
    app.state.store = store
    app.state.timeline = timeline
    app.state.bus = bus
    app.state.service = service
    app.state.plivo_client = plivo_client

    for name in ("answer", "otp", "otp_timeout", "language", "language_timeout",
                 "action", "action_timeout", "action_menu", "hangup", "fallback", "dial_status"):
        logger.info("callback url resolved: %s -> %s", name, getattr(urls, name))

    yield


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Plivo IVR Console", lifespan=lifespan)

    app.include_router(voice_router)
    app.include_router(calls_router)
    app.include_router(events_router)
    app.include_router(ws_router)

    @app.exception_handler(Exception)
    async def voice_safe_exception_handler(request: Request, exc: Exception) -> Response:
        logger.exception("unhandled exception in %s", request.url.path)
        if request.url.path.startswith(VOICE_PREFIXES):
            return Response(
                content=error_document(), media_type="application/xml", status_code=200
            )
        return Response(
            content='{"detail":"internal server error"}',
            media_type="application/json",
            status_code=500,
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/config")
    async def config(settings: Settings = Depends(get_settings_dep)) -> dict[str, str | None]:
        return {
            "from_number": settings.plivo_from_number,
            "default_destination": settings.default_destination,
            "associate_number": settings.associate_number,
            "demo_otp_code": settings.otp_code if settings.demo_mode else None,
        }

    dist_dir = Path(__file__).resolve().parent.parent / "web" / "dist"
    if dist_dir.exists():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")

    return app


app = create_app()
