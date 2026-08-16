"""Data held per call. Plain dataclasses, no ORM, because the store is in
process and there is nothing here that needs a query language.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

from app.ivr.states import CallState


class Locale(StrEnum):
    EN = "en"
    ES = "es"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DTMFEntry:
    level: str
    digits: str
    accepted: bool
    at: datetime = field(default_factory=utcnow)


@dataclass
class CallEvent:
    type: str
    call_uuid: str
    payload: dict
    at: datetime = field(default_factory=utcnow)

    def to_json(self) -> dict:
        return {
            "type": self.type,
            "call_uuid": self.call_uuid,
            "at": self.at.isoformat(),
            **self.payload,
        }


@dataclass
class CallSession:
    call_uuid: str
    to_number: str
    from_number: str
    otp_code: str
    state: CallState = CallState.AWAITING_OTP
    locale: Locale | None = None
    otp_attempts: int = 0
    authenticated_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    ended_at: datetime | None = None
    hangup_cause: str | None = None
    dtmf_log: list[DTMFEntry] = field(default_factory=list)

    @property
    def is_authenticated(self) -> bool:
        return self.authenticated_at is not None

    def touch(self) -> None:
        self.updated_at = utcnow()
