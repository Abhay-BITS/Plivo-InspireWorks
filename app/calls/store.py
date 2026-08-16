"""Session storage behind a protocol.

The in process dict implementation is what runs today. The protocol is
what makes the README's claim that Redis is a drop in swap an honest one:
anything that implements get, put, delete, and all_active can replace
_InMemoryCallStateStore without touching a single caller. See
docs/ARCHITECTURE.md for what actually changes to run more than one
instance.
"""

import asyncio
from datetime import timedelta
from typing import Protocol

from app.calls.models import CallSession, utcnow


class CallStateStore(Protocol):
    async def get(self, call_uuid: str) -> CallSession | None: ...

    async def put(self, session: CallSession) -> None: ...

    async def delete(self, call_uuid: str) -> None: ...

    async def all_active(self) -> list[CallSession]: ...


class InMemoryCallStateStore:
    def __init__(self, ttl_minutes: int = 30) -> None:
        self._sessions: dict[str, CallSession] = {}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._lock = asyncio.Lock()

    async def get(self, call_uuid: str) -> CallSession | None:
        async with self._lock:
            return self._sessions.get(call_uuid)

    async def put(self, session: CallSession) -> None:
        async with self._lock:
            self._sessions[session.call_uuid] = session

    async def delete(self, call_uuid: str) -> None:
        async with self._lock:
            self._sessions.pop(call_uuid, None)

    async def all_active(self) -> list[CallSession]:
        async with self._lock:
            return [s for s in self._sessions.values() if s.ended_at is None]

    async def evict_expired(self) -> int:
        cutoff = utcnow() - self._ttl
        async with self._lock:
            expired = [uuid for uuid, s in self._sessions.items() if s.created_at < cutoff]
            for uuid in expired:
                del self._sessions[uuid]
            return len(expired)

    async def run_eviction_loop(self, interval_seconds: int = 60) -> None:
        while True:
            await asyncio.sleep(interval_seconds)
            await self.evict_expired()
