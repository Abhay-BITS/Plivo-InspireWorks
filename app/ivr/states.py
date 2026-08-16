"""The states a call can be in.

Named for what the caller is currently doing, not for internal bookkeeping.
Retries are a counter on the session, not a state, because a wrong code
leaves the caller in exactly the same place they were before it: waiting
at the code prompt. Modelling a retry as its own state would double the
transition table without changing what the caller hears or where they can
go next. Authentication is the same story: it is a boolean plus a
timestamp on the session, because the caller is never sitting in
"authenticated" without also being in a menu, so it never earns a node
of its own on the graph.
"""

from enum import StrEnum


class CallState(StrEnum):
    AWAITING_OTP = "AWAITING_OTP"
    LANGUAGE_MENU = "LANGUAGE_MENU"
    ACTION_MENU = "ACTION_MENU"
    PLAYING_AUDIO = "PLAYING_AUDIO"
    TRANSFERRING = "TRANSFERRING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


TERMINAL_STATES = frozenset({CallState.COMPLETED, CallState.FAILED})
