#!/usr/bin/env python3
"""Drives the whole IVR against the ASGI app in process, no Plivo and no
phone involved. Prints every prompt and every XML document served, with
the state transition between them, so any path can be replayed in a
second while debugging.

Usage:
    python scripts/simulate_call.py --digits 9999,0407,2,1
    python scripts/simulate_call.py --digits 0407,timeout,1,1

Each comma separated token is either digits sent to whichever endpoint
matches the caller's current level, or the literal "timeout" to simulate
silence at that level.
"""

import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("PLIVO_AUTH_ID", "simulator")
os.environ.setdefault("PLIVO_AUTH_TOKEN", "simulator")
os.environ.setdefault("VERIFY_PLIVO_SIGNATURE", "false")
os.environ.setdefault("PUBLIC_BASE_URL", "http://localhost:8000")

import httpx  # noqa: E402

from app.ivr.states import CallState  # noqa: E402
from app.main import create_app  # noqa: E402

ENDPOINT_BY_STATE = {
    CallState.AWAITING_OTP: ("/voice/otp", "/voice/otp-timeout"),
    CallState.LANGUAGE_MENU: ("/voice/language", "/voice/language-timeout"),
    CallState.ACTION_MENU: ("/voice/action", "/voice/action-timeout"),
}


def _print_step(label: str, xml: str) -> None:
    print(f"\n--- {label} ---")
    pretty = ET.tostring(ET.fromstring(xml), encoding="unicode")
    print(pretty)


async def run(digit_tokens: list[str]) -> None:
    app = create_app()
    call_uuid = f"sim-{uuid.uuid4()}"
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        async with app.router.lifespan_context(app):
            service = app.state.service
            form = {"CallUUID": call_uuid, "To": "+917007745038", "From": "+918035454161"}

            resp = await client.post("/voice/answer", data=form)
            _print_step("answer", resp.text)

            for token in digit_tokens:
                session = await service.get_session(call_uuid)
                assert session is not None
                action_url, timeout_url = ENDPOINT_BY_STATE.get(
                    session.state, ("/voice/action-menu", "/voice/action-menu")
                )
                from_state = session.state

                if token == "timeout":
                    resp = await client.post(timeout_url, data=form)
                    label = f"{timeout_url}  (silence at {from_state.value})"
                else:
                    resp = await client.post(action_url, data={**form, "Digits": token})
                    label = f"{action_url}  Digits={token}  (at {from_state.value})"

                session = await service.get_session(call_uuid)
                assert session is not None
                print(f"\n[state] {from_state.value} -> {session.state.value}")
                _print_step(label, resp.text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--digits",
        required=True,
        help="comma separated digit groups or 'timeout', e.g. 9999,0407,2,1",
    )
    args = parser.parse_args()
    tokens = [t.strip() for t in args.digits.split(",") if t.strip()]
    asyncio.run(run(tokens))


if __name__ == "__main__":
    main()
