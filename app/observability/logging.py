"""JSON logging with call_uuid bound via contextvars, so every log line
inside a request handling a webhook carries the call it belongs to
without threading the value through every function signature.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_call_uuid_ctx: ContextVar[str | None] = ContextVar("call_uuid", default=None)


def bind_call_uuid(call_uuid: str | None) -> None:
    _call_uuid_ctx.set(call_uuid)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "at": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        call_uuid = _call_uuid_ctx.get()
        if call_uuid:
            payload["call_uuid"] = call_uuid
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
