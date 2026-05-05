# OBD-II Data Viewer Application

A Python terminal app for connecting to a Bluetooth ELM327-style OBD-II adapter, polling live vehicle PIDs, decoding the responses, and showing them in a continuously updating dashboard.

The project also includes a built-in simulator so you can work on the polling, parsing, and dashboard experience without needing a car or BLE adapter connected.

## Features

- Scan for nearby BLE devices and choose one interactively
- Connect to a real ELM327-compatible Bluetooth OBD-II adapter with `bleak`
- Send initialization commands such as `ATZ` and `ATE0`
- Poll a set of Mode 01 OBD-II PIDs in a loop
- Decode raw hex responses into human-readable values
- Decode lookup-style values such as OBD compliance standard and fuel type
- Display live results in a Rich-powered terminal dashboard
- Run in simulation mode with a mock `BleakClient` that supports the same live PID set
- Buffer and clean noisy adapter output such as `OK`, `SEARCHING...`, and echoed commands

## Current PIDs Displayed

The default dashboard polls and displays:

- `0104`: Engine Load (`%`)
- `0105`: Coolant Temperature (`°C`)
- `010B`: Intake Manifold Pressure (`kPa`)
- `010C`: Engine RPM (`rpm`)
- `010D`: Vehicle Speed (`km/h`)
- `010F`: Intake Air Temperature (`°C`)
- `0110`: MAF Air Flow Rate (`g/s`)
- `0111`: Throttle Position (`%`)
- `011C`: OBD Standard
- `011F`: Run Time Since Engine Start (`s`)
- `0123`: Fuel Rail Gauge Pressure (`kPa`)
- `012F`: Fuel Tank Level (`%`)
- `0142`: Control Module Voltage (`V`)
- `0143`: Absolute Load (`%`)
- `0144`: Commanded Equivalence Ratio
- `0146`: Ambient Air Temperature (`°C`)
- `0149`: Accelerator Pedal Position D (`%`)
- `0151`: Fuel Type
- `015C`: Engine Oil Temperature (`°C`)
- `015D`: Fuel Injection Timing (`°`)
- `0161`: Driver Demand Engine Torque (`%`)

These are configured in [PID_Resources/pid_list.py](../PID_Resources/pid_list.py) and decoded in [PID_Resources/pid_decoder.py](../PID_Resources/pid_decoder.py).

## PID Decoder Functionality

The decoder currently supports Mode 01 `41 xx ...` responses for all PIDs in the dashboard list. It:

- extracts valid Mode 01 responses from noisy ELM327 text
- ignores unsupported or incomplete responses by returning `None`
- converts hex data bytes using PID-specific formulas
- rounds floating-point values to two decimal places
- maps OBD standard byte values to readable labels
- maps fuel type byte values to readable labels

String-valued PIDs such as OBD Standard and Fuel Type are displayed without numeric rounding.

## Simulator PID Support

Simulation mode responds to every PID in the default polling list with randomized, realistic-looking values. It also includes supported-PID bitmask responses for:

- `0100`: supported PIDs `01-20`
- `0120`: supported PIDs `21-40`
- `0140`: supported PIDs `41-60`
- `0160`: supported PIDs `61-80`

The simulator also has a Mode 09 VIN response for `0902`, though the live dashboard currently polls only Mode 01 PIDs.

## Project Structure

- [main.py](../main.py): app entry point, BLE discovery, connection, polling loop, and live dashboard updates
- [obd2_simulator.py](../obd2_simulator.py): mock ELM327/BLE client for offline development
- [intialization_commands.py](../intialization_commands.py): startup commands sent to the adapter
- [PID_Resources/pid_list.py](../PID_Resources/pid_list.py): list of requested PIDs
- [PID_Resources/pid_decoder.py](../PID_Resources/pid_decoder.py): response parsing and PID-specific decode formulas
- [dashboard/dashboardData.py](../dashboard/dashboardData.py): dashboard data store and Rich table builder
- [Bluetooth_testing.py](../Bluetooth_testing.py): older BLE experimentation file kept for reference
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

This project includes `uv` project metadata in [pyproject.toml](../pyproject.toml), a lockfile in [uv.lock](../uv.lock), and a console command named `obd2-viewer`.

On macOS, install `uv` with Homebrew if the command is not already available:

```bash
brew install uv
```

Then install the project dependencies with:

```bash
uv sync
```

Run the app with:

```bash
uv run obd2-viewer
```

If you are not using `uv`, create a virtual environment and install the dependencies with:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install bleak rich
```

## Running The Project

Start the app with:

```bash
uv run obd2-viewer
```

By default, the app runs in normal BLE mode and scans for nearby named devices.

## CLI Options

The app supports common runtime configuration through command-line flags:

- `--simulate`: run with the built-in mock OBD/BLE simulator
- `--debug`: enable verbose logging for discovery, characteristics, PID requests, and ignored adapter chatter
- `--poll-delay <seconds>`: control the delay between PID requests
- `--device-name "<name>"`: connect to the first BLE device whose advertised local name exactly matches the given value
- `--device-address <address>`: connect directly to a BLE adapter by address
- `--scan-timeout <seconds>`: control how long BLE discovery runs in real mode

See the built-in help with:

```bash
uv run obd2-viewer --help
```

### Real Adapter Mode

Run in normal BLE mode with interactive device selection:

```bash
uv run obd2-viewer
```

Or target a specific adapter by name:

```bash
uv run obd2-viewer --device-name "OBDII"
```

Or connect directly by address:

```bash
uv run obd2-viewer --device-address "AA:BB:CC:DD:EE:FF"
```

In real adapter mode, the app:

- scans for nearby BLE devices
- shows named devices it finds
- prompts you to choose one if you did not provide `--device-name` or `--device-address`
- connects using `BleakClient`

### Simulation Mode

To run without hardware:

```bash
uv run obd2-viewer --simulate
```

In simulation mode, the app:

- skips BLE scanning
- uses `MockBleakClient`
- returns randomized but realistic-looking OBD-II values
- lets you test the dashboard and decoder loop locally

## Example Workflow

1. Run `uv sync` once to create the environment and install dependencies.
2. Run `uv run obd2-viewer --simulate` to test without hardware.
3. Run `uv run obd2-viewer` to use interactive BLE discovery.
4. Optionally target an adapter with `uv run obd2-viewer --device-name "OBDII"`.
5. Optionally slow polling with `uv run obd2-viewer --poll-delay 0.25`.
6. Press `Ctrl+C` to stop the loop.

## Example Commands

```bash
uv run obd2-viewer --simulate
uv run obd2-viewer --debug
uv run obd2-viewer --poll-delay 0.25
uv run obd2-viewer --device-name "OBDII"
uv run obd2-viewer --device-address "AA:BB:CC:DD:EE:FF"
uv run obd2-viewer --scan-timeout 8
```

## Adding Or Changing PIDs

To add a new PID:

1. Add the command to [PID_Resources/pid_list.py](../PID_Resources/pid_list.py).
2. Add a matching entry to `PID_DEFINITIONS` in [PID_Resources/pid_decoder.py](../PID_Resources/pid_decoder.py).
3. Include:
   - `name`
   - `unit`
   - number of data `bytes`
   - a `decode` lambda or function

For simulator parity, add a response generator and `MODE_01` entry in [obd2_simulator.py](../obd2_simulator.py) for the same command.

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

- There is no `requirements.txt` yet for non-`uv` installs.
- The app currently chooses the first writable and first notify characteristic it sees. Some adapters may require more specific UUID selection logic.
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

- Add a `requirements.txt` for non-`uv` users
- Add preferred UUID matching for known OBD-II adapters
- Expand decoder support for more PIDs and Mode 09 data
- Add logging and debug verbosity levels
- Export captured data to CSV or JSON
- Build a graphical dashboard

## Status

This project is a solid working prototype for live OBD-II polling over BLE with a terminal dashboard and simulator-backed development flow.
