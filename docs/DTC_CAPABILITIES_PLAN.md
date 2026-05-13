# DTC Capabilities Plan

## Why This Matters

The current app is a live OBD-II data viewer. It connects to an adapter, polls
Mode 01 PIDs, decodes live values, and displays them in a terminal dashboard.

DTC support is the next important step toward a real diagnostic assistant.
Instead of only showing live data, the app will also be able to ask the vehicle
for stored diagnostic trouble codes and use those codes as evidence in future
guided diagnostic workflows.

Feeling overwhelmed at this stage is normal. The project is moving from a small
script into a layered application with Bluetooth transport, OBD protocol
handling, parsing, simulation, dashboard display, and eventually diagnostics.
The way to keep it manageable is to build one layer at a time.

## Goal

Add the ability to request stored DTCs from the vehicle, decode the raw response,
and display the codes once when the app starts.

First milestone:

```text
connect
-> initialize ELM327 adapter
-> send "03\r"
-> receive a response such as "43 01 33 03 00 00 00"
-> decode it into ["P0133", "P0300"]
-> print stored DTCs
-> continue into the live PID dashboard
```

## OBD Modes To Know

The app currently focuses on Mode 01:

```text
01xx = current live powertrain data
```

Examples:

```text
010C = engine RPM
010D = vehicle speed
0142 = control module voltage
```

DTCs use different modes:

```text
03 = request stored DTCs
07 = request pending DTCs
0A = request permanent DTCs
04 = clear DTCs
```

For the first version, only implement Mode 03.

Do not add Mode 04 clearing yet. Clearing DTCs is destructive from a diagnostic
standpoint because it can erase useful evidence such as freeze frame data and
readiness state.

## How DTC Responses Work

If the app sends:

```text
03
```

The vehicle may respond with:

```text
43 01 33 00 00 00 00
```

The response mode is the request mode plus `40`.

```text
03 request -> 43 response
01 request -> 41 response
```

DTCs are encoded in two-byte chunks.

Example:

```text
01 33
```

decodes to:

```text
P0133
```

The first two bits of the first byte decide the code family:

```text
00 = P = Powertrain
01 = C = Chassis
10 = B = Body
11 = U = Network
```

The remaining bits create the numeric portion of the code.

Zero pairs should be ignored:

```text
00 00 = no DTC in this slot
```

## Phase 1: Add A DTC Decoder

Create a new diagnostics package:

```text
diagnostics/
  __init__.py
  dtc_decoder.py
```

Recommended functions:

```python
def decode_dtc_bytes(first_byte: int, second_byte: int) -> str:
    ...
```

and:

```python
def decode_dtc_response(response: str) -> list[str]:
    ...
```

Responsibility:

```text
raw DTC response text -> list of DTC strings
```

Example:

```python
decode_dtc_response("43 01 33 00 00 00 00")
```

should return:

```python
["P0133"]
```

Keep this file heavily commented. The important learning topics are:

- converting hex strings to integers with `int(value, 16)`
- using lists of strings
- splitting bytes into two-byte DTC chunks
- ignoring `00 00`
- bitwise operations for decoding the DTC family and number

## Phase 2: Add Simulator Support

Update `obd2_simulator.py` so the simulator understands:

```text
03
```

Possible implementation shape:

```python
def _mode_03_stored_dtcs():
    return "43 01 33 03 00 00 00"
```

Then update `_build_response()` so it can return that response when the command
is `03`.

This allows DTC work to be tested without a real car or adapter.

## Phase 3: Request DTCs Once At Startup

The current live dashboard loop sends Mode 01 PIDs forever.

DTCs should not be spammed in the same loop. For the first version, request them
once after initialization and before the live dashboard starts.

Flow:

```text
connect
-> initialize adapter
-> request stored DTCs once
-> print decoded DTCs
-> start live PID dashboard
```

This keeps the first version simple and easy to understand.

## Phase 4: Store DTCs In Application State

At first, a plain list is enough:

```python
stored_dtcs = ["P0133", "P0300"]
```

Later, this can become part of a bigger vehicle session object:

```python
vehicle_session = {
    "vin": None,
    "dtcs": [],
    "live_data": {},
    "technician_notes": [],
}
```

Do not jump to the full session model immediately unless the simple DTC flow is
working first.

## Phase 5: Display DTCs Nicely

First version can print:

```text
Stored DTCs:
- P0133
- P0300
```

Later version can use a Rich table:

```text
Stored Diagnostic Trouble Codes
Code    Description
P0133   Description not loaded yet
P0300   Description not loaded yet
```

Descriptions should be a separate future step. Decoding a code and knowing what
the code means are different responsibilities.

## Files Likely To Change

```text
diagnostics/dtc_decoder.py
```

New file for DTC decoding logic.

```text
diagnostics/__init__.py
```

New package export file.

```text
obd2_simulator.py
```

Teach simulator how to respond to Mode 03.

```text
main.py
```

Send the DTC request after initialization and print decoded results.

```text
docs/README.md
```

Document DTC support once implemented.

## What Not To Add Yet

Avoid adding these in the first DTC milestone:

- clearing codes
- pending codes
- permanent codes
- freeze frame
- DTC descriptions
- LLM diagnostic advice
- GUI display
- manufacturer-specific codes

Those are valuable, but adding them all at once would make the project harder to
understand and harder to debug.

## Recommended First Commit

Build only:

```text
Mode 03 stored DTC request and decoder
```

Possible commit message:

```text
Add stored DTC decoding support
```

Possible commit body:

```text
- Add DTC decoder for Mode 03 responses
- Add simulator response for stored DTC requests
- Request stored DTCs once after adapter initialization
- Print decoded DTCs before starting the live dashboard
```

## Future Direction

Once stored DTC support works, the app can move toward a diagnostic assistant:

```text
DTCs + live PID snapshots + vehicle info + symptom selection
-> guided diagnostic workflow
-> LLM-assisted explanation and next steps
```

The important design rule:

```text
Python should handle measurement, parsing, structure, and rules.
The LLM should explain, guide, and summarize evidence.
```

