# Demo video shot list

Timed to four minutes. Cut phone audio in cleanly; the dashboard visuals
can be trimmed more freely than the call audio.

| Time | Shot |
| --- | --- |
| 0:00-0:15 | Console at rest: empty timeline, "No calls yet" message, the destination field prefilled. |
| 0:15-0:30 | Enter the number (or accept the prefilled one), click Place call. Toast confirms "Call placed." |
| 0:30-0:50 | Phone ringing, dashboard already shows the new call in the active list with a running duration. |
| 0:50-1:10 | Answer. Code prompt heard. Enter a wrong code (`9999`), dashboard marks the digit chip rejected, phone repeats the prompt. |
| 1:10-1:35 | Deliberate silence through one full timeout window. No further input from the caller; dashboard shows the state stayed at `AWAITING_OTP` and the timeline logs the re-prompt. This is the shot that proves the no input handling works. |
| 1:35-1:50 | Enter the correct code (`0407`). Graph draws the edge into the language menu, XML panel updates. |
| 1:50-2:10 | Press 1 for English (or 2, whichever the first call did not use on a rerun). |
| 2:10-2:35 | Press 1 for the audio message. Let it play to completion, show it returning to the action menu on its own rather than hanging up. |
| 2:35-2:45 | Hang up. Dashboard shows `call_ended` and the final duration. |
| 2:45-3:20 | Second call: repeat answer and code entry quickly (can be sped up in edit), then press 2 for the transfer. Show the associate line ringing and connecting. |
| 3:20-3:30 | Hang up the second call. |
| 3:30-4:00 | Cut to terminal: `make check` running green, then `app/ivr/machine.py` on screen with a few seconds to let the state names and the single `advance()` function register. |

Cut points: everywhere the caller is not actively speaking or listening,
after the transition has visibly landed on the dashboard. Never cut mid
ring or mid `Speak`, since that is exactly the audio a reviewer needs to
hear to trust the recording is real.
