# OBD2 BLE Debugging Conversation Notes

Date: March 20–21, 2026
Project: OBD2 Data Viewer Application

## Why this note exists
You asked why you were seeing repeated **"Received unrecognized response"** messages even when not in simulation mode, and then asked to preserve the discussion for later learning.

---

## 1) What was happening
You were seeing output like:
- Characteristic discovery logs
- `TX_UUID` / `RX_UUID` selection
- Initialization commands (`ATZ`, `ATE0`, `ATL0`, `ATH0`, `ATSP0`)
- Repeated lines like `SEARCHING...`, `OK`, echoes, and prompt-related fragments
- Frequent logs: `Received unrecognized response`

### Core reason
This was **real BLE adapter traffic** (not simulation), because `simulation_on = False` in `main.py`.

In real ELM327 sessions, responses include control text such as:
- `AT...` command echoes
- `OK`
- `SEARCHING...`
- prompt `>`
- device ID text like `ELM327 v2.3`

Your decoder only recognizes Mode 01 PID data beginning with `41`, so all non-PID control chatter was being logged as unrecognized.

---

## 2) How `decode_response` works (original behavior)
Function: `PID_Resources/pid_decoder.py`

Expected input format:
- `41 <PID> <data bytes...>`

Example valid responses:
- `41 05 6E` → coolant temp
- `41 0C 1A F8` → RPM
- `41 0D 3C` → speed

Original flow:
1. Trim/split text into tokens.
2. Require first token to be `41`; otherwise return `None`.
3. Read PID from token index 1.
4. Verify PID exists in `PID_DEFINITIONS`.
5. Parse required number of hex data bytes.
6. Apply PID-specific decode formula.
7. Return structured dict: `pid`, `name`, `value`, `unit`.

Why non-PID lines failed:
- Lines like `OK`, `SEARCHING...`, `ATZ`, `ELM327 v2.3` do not start with `41`.

---

## 3) Changes you approved (and were applied)
You asked to apply all proposed changes **except** UUID preference logic. That is exactly what was done.

### A) Notification parsing improvements in `main.py`
Implemented:
- Added an `rx_buffer` to accumulate fragmented BLE notifications.
- Split buffered text using `\r`, `\n`, and `>` as separators.
- Ignored expected control chatter:
  - `AT...`
  - `OK`
  - `SEARCHING...`
  - `NO DATA`
  - `?`
  - `ELM327...`
- Decoded only meaningful lines.
- Reduced noisy log spam by printing `Ignored non-PID line: ...` only for unexpected leftovers.

Why this helps:
- BLE packets can arrive in chunks; a single OBD line may be split across notifications.
- Prompt/echo/control messages are normal and should not be treated as decoder failures.

### B) Safer parsing in `PID_Resources/pid_decoder.py`
Implemented:
- Added regex-based extraction for embedded Mode 01 frames (`41 xx ...`) from noisy text.
- Normalized input to uppercase before parsing.
- Added guards for incomplete/short frames to avoid indexing problems.
- Continued returning `None` safely for non-decodable input.

Why this helps:
- Makes parser resilient when valid PID frames are mixed with extra adapter text.
- Prevents crashes from partial or malformed responses.

---

## 4) What was intentionally NOT changed
Per your request, we did **not** add preferred known OBD UUID pairing logic.

Existing behavior remains:
- First writable characteristic picked as `TX_UUID`.
- First notify/indicate characteristic picked as `RX_UUID`.

---

## 5) Learning takeaways
1. **Real OBD adapters produce control chatter**; parsing logic must separate control-plane text from data-plane PID frames.
2. **Transport framing matters** over BLE notifications; build line buffers before decoding.
3. **Parser robustness** should include:
   - normalization
   - frame extraction
   - short-frame guards
4. Keep logs actionable:
   - expected chatter should be filtered
   - unexpected lines should be visible (optionally behind a debug flag)

---

## 6) Suggested next improvement (optional)
Add a small debug toggle in `main.py` to turn ignored-line logging on/off without code edits.

---

## 7) Encouragement
You asked thoughtful questions in the right order:
- first root cause,
- then parser understanding,
- then controlled code changes.

That sequence is exactly how strong debugging habits are built.
