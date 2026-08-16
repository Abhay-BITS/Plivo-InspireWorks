"""Append only per call event log, kept in memory so a browser connecting
mid call can be replayed the last fifty events instead of seeing nothing.
"""

from collections import defaultdict, deque

from app.calls.models import CallEvent

MAX_EVENTS_PER_CALL = 50


class Timeline:
    def __init__(self) -> None:
        self._events: dict[str, deque[CallEvent]] = defaultdict(
            lambda: deque(maxlen=MAX_EVENTS_PER_CALL)
        )

    def record(self, event: CallEvent) -> None:
        self._events[event.call_uuid].append(event)

    def history(self, call_uuid: str) -> list[CallEvent]:
        return list(self._events.get(call_uuid, ()))
