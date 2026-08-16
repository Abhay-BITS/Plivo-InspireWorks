# Architecture

## Layering

```
app/
  telephony/     talks in Plivo's vocabulary: XML documents, the REST
                 client, signature validation, the prompt catalogue.
                 Knows nothing about HTTP routing or session storage.

  ivr/           the product. states.py defines what a caller can be
                 doing, machine.py is one pure function that decides
                 what happens next, handlers.py turns that decision into
                 XML by calling telephony/xml_builder.py. Nothing in
                 this package imports FastAPI or plivo.

  calls/         session storage, orchestration, and rate limiting.
                 service.py is the only place that touches the store,
                 the machine, and the event bus in the same function.

  api/           FastAPI routers. Each handler validates a signature,
                 parses a form, calls into calls/service.py, and returns
                 whatever service.py gave it. No branching lives here.

  observability/ structured logging and the per call event timeline.
```

The dependency direction only ever points down this list. `api` depends on
`calls`, which depends on `ivr` and `telephony`, which depend on nothing
in this project. A route handler that reaches past `calls/service.py` into
`ivr/machine.py` directly, or that builds XML by hand, is a sign something
has drifted from this layering.

## Why the machine is isolated

`app/ivr/machine.py` has no import of FastAPI, Plivo, or anything async.
`advance(session, event)` takes a plain dataclass and a session, and
returns a plain dataclass. This is what makes `test_state_machine.py` able
to cross every state with every kind of input without standing up a
server, and it is what makes the file readable end to end as the
specification for the product rather than a description of it.

## How state is keyed and evicted

Every session lives behind `app.calls.store.CallStateStore`, a Protocol
with four methods: `get`, `put`, `delete`, `all_active`. The implementation
running today, `InMemoryCallStateStore`, is a dict keyed by Plivo's
`CallUUID`, guarded by an `asyncio.Lock` so concurrent webhooks for
different calls never interleave a read and a write on the same
dictionary. A background task calls `evict_expired` on an interval,
removing any session older than `SESSION_TTL_MINUTES` (default thirty).

Two calls in flight at once are simply two entries in the dict. There is
no shared mutable state between them, which is what
`test_concurrent_calls.py` asserts directly: interleaved webhooks for two
`CallUUID`s never contaminate each other's `otp_attempts` or `locale`.

## What changes to run more than one instance

The in memory store is a single process's dictionary, so a second
instance behind the same load balancer would not see the first instance's
sessions. Two changes make that work, and both are small because of the
protocol:

1. **Sticky sessions**, so a given `CallUUID`'s webhooks always land on
   the instance that created it. This is the zero code change option and
   is enough for a small deployment.
2. **A shared store**, most naturally Redis: a `RedisCallStateStore` that
   implements the same four methods (`get`/`put` as `GET`/`SETEX`,
   `all_active` as a scan over a key pattern) is a drop in replacement for
   `InMemoryCallStateStore` wherever it is constructed in `app/main.py`.
   No caller of the store, anywhere in `calls/service.py` or the route
   handlers, would need to change, because they only ever see the
   `CallStateStore` protocol.

The same story applies to `EventBus` and to `DestinationRateLimiter`: both
are in process today, and both would need a shared backend (Redis pub/sub
for the bus, `INCR` with a TTL for the limiter) to work correctly across
more than one instance.

## Request lifecycle

See `docs/CALL_FLOW.md` for the full sequence with literal XML at each
step. In short: the browser triggers an outbound call, Plivo answers and
walks the caller through `answer` to `otp` to `language` to `action`, with
a parallel timeout endpoint at every level so silence re-prompts instead
of ending the call. Every step calls into `CallService.handle_webhook`,
which advances the machine, renders XML, and publishes a `CallEvent` to
whatever is connected to `/ws/live`.
