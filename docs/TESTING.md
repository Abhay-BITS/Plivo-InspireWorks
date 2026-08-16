# Testing

## Running the suite

```
make check
```

runs `ruff check`, `mypy app/`, and `pytest` with coverage on
`app/ivr` and `app/telephony`. Individually:

```
pytest                       # all tests
pytest tests/test_otp_flow.py -v
pytest --cov=app.ivr --cov=app.telephony --cov-report=term-missing
```

No test in the suite places a real call. `test_api_calls.py` mocks the
Plivo REST client; every other test drives the ASGI app directly with
`httpx.AsyncClient`, posting the same form encoded payloads Plivo sends to
a webhook.

## Using the simulator

```
python scripts/simulate_call.py --digits 9999,0407,2,1
```

Each comma separated token is either digits sent to whichever endpoint
matches the caller's current level, or the literal `timeout` to simulate
silence. It drives the whole IVR against the ASGI app in process, no
tunnel and no phone required, and prints the state transition and the
served XML at every step. This is the fastest way to check a change: a
full path replays in under a second.

Two sequences worth running after touching `app/ivr/machine.py`:

```
python scripts/simulate_call.py --digits timeout,timeout,0407,1,timeout,1,9,2
python scripts/simulate_call.py --digits abc,0000,0407,5,timeout,9,timeout
```

Neither should ever print `<Hangup/>` except at the very end of a
deliberately triggered error.

## Manual script for the demo video

1. Start the API (`make run`) and the console (`cd web && npm run dev`),
   or `docker compose up`.
2. Open the console, confirm the connection dot reads connected.
3. Place a call to the prefilled destination.
4. When it rings, let it go to voicemail on purpose once, confirm the
   dashboard still shows a clean state rather than an error.
5. On the real answer: enter `9999` first, confirm the retry line and the
   dashboard's dtmf chip mark it rejected.
6. Stay silent through one full timeout window, confirm the console shows
   a repeated `AWAITING_OTP` state and the caller hears the prompt again.
7. Enter `0407`, confirm the graph draws the edge into the language menu.
8. Press `2` for Spanish, confirm the served XML panel shows `es-ES` and
   Spanish text.
9. Press `1` for the audio clip, let it finish, confirm it returns to the
   action menu on its own.
10. Press `2` for the transfer, confirm the associate line rings.
11. Hang up, confirm the graph and timeline both show `call_ended`.
12. Place a second call for the transfer path if the first one covered
    audio instead, so both leaf paths are on camera at least once across
    the two calls.
