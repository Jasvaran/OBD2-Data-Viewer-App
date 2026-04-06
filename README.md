# OBD-II Data Viewer Application

A Python terminal app for connecting to a Bluetooth ELM327-style OBD-II adapter, polling live vehicle PIDs, decoding the responses, and showing them in a continuously updating dashboard.

The project also includes a built-in simulator so you can work on the polling, parsing, and dashboard experience without needing a car or BLE adapter connected.

## Features

- Scan for nearby BLE devices and choose one interactively
- Connect to a real ELM327-compatible Bluetooth OBD-II adapter with `bleak`
- Send initialization commands such as `ATZ` and `ATE0`
- Poll a set of Mode 01 OBD-II PIDs in a loop
- Decode raw hex responses into human-readable values
- Display live results in a Rich-powered terminal dashboard
- Run in simulation mode with a mock `BleakClient`
- Buffer and clean noisy adapter output such as `OK`, `SEARCHING...`, and echoed commands

## Current PIDs Displayed

The default dashboard polls and displays:

- Coolant Temperature
- Engine RPM
- Vehicle Speed
- Engine Load
- Intake Manifold Pressure
- Intake Air Temperature
- Throttle Position
- Fuel Tank Level
- Ambient Air Temperature

These are configured in [PID_Resources/pid_list.py](PID_Resources/pid_list.py) and decoded in [PID_Resources/pid_decoder.py](PID_Resources/pid_decoder.py).

## Project Structure

- [main.py](main.py): app entry point, BLE discovery, connection, polling loop, and live dashboard updates
- [obd2_simulator.py](obd2_simulator.py): mock ELM327/BLE client for offline development
- [intialization_commands.py](intialization_commands.py): startup commands sent to the adapter
- [PID_Resources/pid_list.py](PID_Resources/pid_list.py): list of requested PIDs
- [PID_Resources/pid_decoder.py](PID_Resources/pid_decoder.py): response parsing and PID-specific decode formulas
- [dashboard/dashboardData.py](dashboard/dashboardData.py): dashboard data store and Rich table builder
- [Bluetooth_testing.py](Bluetooth_testing.py): older BLE experimentation file kept for reference
- [LIVE_DASHBOARD_PLAN.md](LIVE_DASHBOARD_PLAN.md): notes on the live dashboard implementation
- [CONVERSATION_STUDY_NOTES.md](CONVERSATION_STUDY_NOTES.md): debugging notes about parsing noisy real adapter output

## How It Works

1. `main.py` scans for nearby named BLE devices.
2. You choose a device from the terminal prompt.
3. The app discovers GATT characteristics and picks:
   - the first writable characteristic as TX
   - the first notify/indicate characteristic as RX
4. Initialization commands are sent to the adapter.
5. The app continuously requests each PID in `PID_LIST`.
6. Incoming BLE notifications are buffered and split into lines.
7. Valid `41 xx ...` Mode 01 responses are decoded into values.
8. The dashboard updates in place using `rich.live.Live`.

## Requirements

- Python 3.11 or newer recommended
- A terminal that supports Rich output
- For real hardware mode:
  - a BLE-capable machine
  - an ELM327-compatible Bluetooth OBD-II adapter
  - Bluetooth permissions enabled for your OS and terminal/Python runtime

Python packages used by the app:

- `bleak`
- `rich`

Install them with:

```bash
pip install bleak rich
```

## Running The Project

Start the app with:

```bash
python main.py
```

By default, the app is currently set to real BLE mode in [main.py](main.py).

### Real Adapter Mode

In the current code:

```python
simulation_on = False
```

With that setting:

- the app scans for nearby BLE devices
- shows named devices it finds
- prompts you to choose one
- connects using `BleakClient`

### Simulation Mode

To run without hardware, change the flag in [main.py](main.py) to:

```python
simulation_on = True
```

In simulation mode, the app:

- skips BLE scanning
- uses `MockBleakClient`
- returns randomized but realistic-looking OBD-II values
- lets you test the dashboard and decoder loop locally

## Example Workflow

1. Open [main.py](main.py).
2. Set `simulation_on` to `True` if you want to test without hardware.
3. Run `python main.py`.
4. Watch the live table refresh with current PID values.
5. Press `Ctrl+C` to stop the loop.

## Adding Or Changing PIDs

To add a new PID:

1. Add the command to [PID_Resources/pid_list.py](PID_Resources/pid_list.py).
2. Add a matching entry to `PID_DEFINITIONS` in [PID_Resources/pid_decoder.py](PID_Resources/pid_decoder.py).
3. Include:
   - `name`
   - `unit`
   - number of data `bytes`
   - a `decode` lambda or function

Example shape:

```python
"XX": {
    "name": "Example PID",
    "unit": "units",
    "bytes": 1,
    "decode": lambda a: a,
}
```

If a PID is in the polling list but not in the decoder, it will not be displayed as decoded dashboard data.

## Notes And Limitations

- There is no `requirements.txt` or `pyproject.toml` yet, so dependencies are not pinned.
- The app currently chooses the first writable and first notify characteristic it sees. Some adapters may require more specific UUID selection logic.
- `simulation_on` is a manual code toggle rather than a CLI argument or config setting.
- Only a subset of Mode 01 PIDs is implemented.
- The main interface is terminal-only; there is no GUI or web frontend yet.
- File naming includes `intialization_commands.py`, which is intentionally referenced as-is in the code even though the word is misspelled.

## Troubleshooting

### No named BLE devices were found

- Make sure the adapter is powered on and advertising
- Move closer to the adapter
- Confirm Bluetooth permissions are granted
- Try scanning again

### You see control text like `OK` or `SEARCHING...`

That is normal for real ELM327 traffic. The app already filters common non-PID chatter before decoding.

### The dashboard shows `N/A`

- The PID may not have returned a valid response yet
- The adapter may not support that PID
- The response may not match a decoder entry yet

### The wrong BLE characteristic is selected

Some adapters expose several characteristics. The current implementation uses a generic first-match strategy, so adapter-specific UUID handling may be needed.

## Future Improvement Ideas

- Add a `requirements.txt` or `pyproject.toml`
- Add command-line flags for simulation mode and scan timeout
- Add preferred UUID matching for known OBD-II adapters
- Expand decoder support for more PIDs and Mode 09 data
- Add logging and debug verbosity levels
- Export captured data to CSV or JSON
- Build a graphical dashboard

## Status

This project is a solid working prototype for live OBD-II polling over BLE with a terminal dashboard and simulator-backed development flow.
