# Design decisions

Numbered, with context, decision, and consequence. Negative decisions (what
was deliberately left out) are included because they carry as much
information as what was built.

## 1. The IVR is a pure state machine, the web layer is a thin adapter

Context: most take home IVR submissions put branching logic inside route
handlers, which makes the flow impossible to read in one sitting and
impossible to unit test without a running server.

Decision: `app/ivr/machine.py` exposes a single pure function,
`advance(session, event) -> Transition`. It imports nothing from FastAPI or
Plivo. Route handlers only validate the signature, parse the form, call
`service.advance_call`, and return XML.

Consequence: the entire product logic is readable in about ninety seconds,
and `test_state_machine.py` exercises every state without an HTTP client.

## 2. Retries is a counter, not a state

Context: a wrong code and a correct code leave the caller in the same
place, waiting at the same prompt.

Decision: `otp_attempts` is a counter on `CallSession`, not a member of
`CallState`. The same reasoning applies to authentication: it is a
timestamp on the session, because the caller is never sitting in
"authenticated" without also being in a menu.

Consequence: the transition table has seven states instead of a much
larger one, and the graph the console draws matches what a person would
actually draw on a whiteboard.

## 3. GetDigits retries is pinned at 1

Context: Plivo's `GetDigits` has its own internal retry count. Left at
its default, a caller who stays silent gets re-prompted by Plivo itself,
invisibly to the application, before the timeout endpoint is ever hit.

Decision: `retries="1"` on every `GetDigits` element, meaning one
collection attempt with no internal Plivo retry. Every re-prompt, whether
from a wrong code or from silence, passes through the state machine and
the timeline.

Consequence: `otp_attempts` and the event timeline are always accurate.
The tradeoff is one extra network round trip per retry compared to
letting Plivo handle it internally, which is negligible next to GetDigits'
own timeout window.

## 4. No database

Context: the assignment runs for the length of a single demo call or a
short review session.

Decision: call state lives in an in process store behind a
`CallStateStore` protocol (`app/calls/store.py`), dict backed, with TTL
eviction. No database, no migrations.

Consequence: state does not survive a restart, which is a real limitation
for a production deployment but not for a live demo, and it is exactly the
gap the protocol exists to close. Swapping in a Redis backed
implementation is adding one file that satisfies the same protocol; see
`docs/ARCHITECTURE.md`.

## 5. No frontend framework

Context: the console is one page: a form, a call list, an SVG graph, a
timeline, and an XML panel.

Decision: vanilla TypeScript built with Vite, no React or similar. The
state graph is a hand authored SVG, not a graph library.

Consequence: the bundle is a few kilobytes and the DOM updates are
explicit and traceable. This would not scale to a multi page application,
which is not what this is.

## 6. Outbound trigger creates a placeholder session, the answer webhook
   creates the real one

Context: `POST /api/calls` gets Plivo's `request_uuid` back immediately,
but the eventual `answer` webhook carries a different id, `CallUUID`,
generated once the call actually connects. There is no reliable way to
correlate the two ahead of time without an extra round trip to Plivo.

Decision: the outbound trigger registers a lightweight session keyed by
`request_uuid` purely so the dashboard shows immediate feedback that a
call was placed. When the answer webhook arrives with the real
`CallUUID`, it does not match any known session, so the existing "unknown
CallUUID" recovery path (section 5.6 of the brief) creates the session
that actually carries the call. The placeholder entry ages out through
normal TTL eviction.

Consequence: one extra row briefly appears in the active call list before
the real one replaces it. Building a correlation handshake instead would
add a round trip to Plivo's REST API and a state field whose entire job is
bridging two ids, for a cosmetic improvement.

## 7. Rate limiting is a sliding window per destination, in process

Context: a demo console that fires a real outbound call on every click can
become a robodialer if someone holds the button down.

Decision: `app/calls/rate_limit.py` allows three calls per destination per
sixty second window, held in memory.

Consequence: multi instance deployment would need a shared counter (Redis
`INCR` with a TTL is the natural choice), which is the same story as the
call store itself.

## 8. Machine detection was left out

Context: section 6.1 of the brief allows enabling Plivo's answering
machine detection, optionally, "only if it tests clean."

Decision: not enabled. It adds latency to call setup and its accuracy
depends on the destination carrier, and it was not something that could
be verified working end to end against the real destination number in the
time available.

Consequence: a call that lands in voicemail plays the full IVR to the
answering machine. This is the documented, deliberate tradeoff of skipping
a feature rather than shipping it half tested.

## 9. Polly voices over the bundled TTS engine

Context: `Speak` audio quality is audible in the first second of the demo
video.

Decision: `Polly.Joanna` for English, `Polly.Conchita` for Spanish,
configured on every `Speak` element.

Consequence: if the connected Plivo account does not have Amazon Polly
enabled, these voice names would need to fall back to the default engine.
This was not hit in testing but is worth checking against the account
before recording.

## 10. Signature validation is built from PUBLIC_BASE_URL, never the
    request object

Context: behind a tunnel, the ASGI request's notion of its own URL
(`localhost`) and the URL Plivo actually called (the tunnel host) disagree.

Decision: every callback URL, and every signature check, is built from
`PUBLIC_BASE_URL` via `app/urls.py`. The request object is never consulted
for its own URL.

Consequence: a stale or misconfigured `PUBLIC_BASE_URL` breaks every
signature check at once, loudly, rather than intermittently. The boot log
prints every resolved callback URL specifically so this is visible in one
glance rather than discovered mid call.
