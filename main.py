import argparse
import asyncio
import pprint

from intialization_commands import init_commands
from obd2_simulator import MockBleakClient
from PID_Resources import decode_response
from PID_Resources import PID_LIST


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Connect to a BLE OBD-II adapter and display live decoded PID data."
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="run with the built-in mock OBD/BLE simulator instead of a real adapter",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable verbose logging for discovery, characteristics, and ignored responses",
    )
    parser.add_argument(
        "--poll-delay",
        type=positive_float,
        default=None,
        help="minimum seconds to pause after each completed PID request",
    )
    parser.add_argument(
        "--response-timeout",
        type=positive_float,
        default=20.0,
        help="seconds to wait for the adapter prompt after each command",
    )
    parser.add_argument(
        "--scan-timeout",
        type=positive_float,
        default=5.0,
        help="seconds to scan for BLE devices in real adapter mode",
    )

    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "--device-name",
        help="connect to the first named BLE device whose local name exactly matches this value",
    )
    target_group.add_argument(
        "--device-address",
        help="connect directly to a BLE device by address without interactive selection",
    )
    parser.add_argument(
        "--tx-uuid",
        help="override the BLE characteristic UUID used for writes",
    )
    parser.add_argument(
        "--rx-uuid",
        help="override the BLE characteristic UUID used for notifications",
    )

    args = parser.parse_args()

    if args.simulate and (args.device_name or args.device_address):
        parser.error("--simulate cannot be combined with --device-name or --device-address")

    return args


def debug_log(enabled: bool, message: str) -> None:
    if enabled:
        print(f"[debug] {message}")


def _uuid_text(uuid: str) -> str:
    return str(uuid).lower()


def _score_write_char(char) -> int:
    uuid = _uuid_text(char.uuid)
    description = getattr(char, "description", "").lower()
    score = 0

    if uuid in {
        "6e400002-b5a3-f393-e0a9-e50e24dcca9e",  # Nordic UART RX/write
        "0000fff2-0000-1000-8000-00805f9b34fb",
        "fff2",
    }:
        score += 100
    if uuid in {
        "0000ffe1-0000-1000-8000-00805f9b34fb",
        "ffe1",
    }:
        score += 80
    if "write" in getattr(char, "properties", []):
        score += 20
    if "write-without-response" in getattr(char, "properties", []):
        score += 10
    if any(word in description for word in ("uart", "serial", "obd", "elm")):
        score += 5

    return score


def _score_notify_char(char) -> int:
    uuid = _uuid_text(char.uuid)
    description = getattr(char, "description", "").lower()
    score = 0

    if uuid in {
        "6e400003-b5a3-f393-e0a9-e50e24dcca9e",  # Nordic UART TX/notify
        "0000fff1-0000-1000-8000-00805f9b34fb",
        "fff1",
    }:
        score += 100
    if uuid in {
        "0000ffe1-0000-1000-8000-00805f9b34fb",
        "ffe1",
    }:
        score += 80
    if "notify" in getattr(char, "properties", []):
        score += 20
    if "indicate" in getattr(char, "properties", []):
        score += 10
    if any(word in description for word in ("uart", "serial", "obd", "elm")):
        score += 5

    return score


def select_characteristics(client, args: argparse.Namespace) -> tuple[str | None, str | None]:
    write_candidates = []
    notify_candidates = []

    for service_index, service in enumerate(client.services):
        for char in service.characteristics:
            props = char.properties
            if "write" in props or "write-without-response" in props:
                write_candidates.append((service_index, char))
            if "notify" in props or "indicate" in props:
                notify_candidates.append((service_index, char))

            debug_log(
                args.debug,
                f"Characteristic: {char.uuid}, Properties: {char.properties}, Description: {char.description}",
            )

    tx_uuid = args.tx_uuid
    rx_uuid = args.rx_uuid

    if tx_uuid is None and write_candidates:
        _, tx_char = max(write_candidates, key=lambda item: _score_write_char(item[1]))
        tx_uuid = tx_char.uuid

    if rx_uuid is None and notify_candidates:
        _, rx_char = max(notify_candidates, key=lambda item: _score_notify_char(item[1]))
        rx_uuid = rx_char.uuid

    if tx_uuid is not None and rx_uuid is not None:
        return tx_uuid, rx_uuid

    return None, None


async def select_device(args: argparse.Namespace) -> str | None:
    from bleak import BleakScanner

    if args.device_address:
        print(f"Using device address from CLI: {args.device_address}")
        return args.device_address

    print(f"Running in real mode. Scanning for BLE devices for {args.scan_timeout:.2f} seconds...")
    devices = await BleakScanner.discover(args.scan_timeout, return_adv=True)

    named_devices = []
    for address, (_, adv_data) in devices.items():
        local_name = adv_data.local_name if adv_data is not None else None
        if local_name:
            named_devices.append((address, local_name))
            debug_log(args.debug, f"Discovered named device: {local_name} ({address})")

    if not named_devices:
        print("No named BLE devices were found. Try scanning again.")
        return None

    if args.device_name:
        normalized_target = args.device_name.casefold()
        matches = [
            (address, local_name)
            for address, local_name in named_devices
            if local_name.casefold() == normalized_target
        ]
        if not matches:
            print(
                f'No BLE device named "{args.device_name}" was found during the scan. '
                "Try a different name, increase --scan-timeout, or choose interactively."
            )
            return None

        address, local_name = matches[0]
        print(f"Selected device by name: {local_name} ({address})")
        return address

    device_dict = {
        index: {"address": address, "name": local_name}
        for index, (address, local_name) in enumerate(named_devices)
    }
    pprint.pprint({index: device["name"] for index, device in device_dict.items()})

    select = input("Enter the number corresponding to the device you want to connect to: ")
    try:
        selection = int(select)
    except ValueError:
        print("Invalid input. Please enter a number. Exiting.")
        return None

    if selection not in device_dict:
        print("Invalid selection. Exiting.")
        return None

    chosen = device_dict[selection]
    print(f"Selected device: {chosen['name']}")
    return chosen["address"]


async def main(args: argparse.Namespace):
    from rich.live import Live

    from dashboard import build_table
    from dashboard import dashboard_dataDict

    simulation_on = args.simulate
    init_delay = 0.2 if simulation_on else 1.0
    poll_delay = args.poll_delay if args.poll_delay is not None else (0.2 if simulation_on else 0.15)
    post_cycle_delay = 0.1 if simulation_on else 0.15

    if simulation_on:
        print("Running in simulation mode. Using MockBleakClient.")
        address = "SIMULATED"
    else:
        from bleak import BleakClient

        address = await select_device(args)
        if address is None:
            return

    ClientClass = MockBleakClient if simulation_on else BleakClient


    async with ClientClass(address) as client:
        print(f"Connected to {address}")

        tx_uuid, rx_uuid = select_characteristics(client, args)

        if tx_uuid is None or rx_uuid is None:
            print("Could not determine TX/RX BLE characteristics for the selected device.")
            return

        debug_log(args.debug, f"TX_UUID: {tx_uuid}")
        debug_log(args.debug, f"RX_UUID: {rx_uuid}")

        # Notification handler function
        prompt_received = asyncio.Event()
        rx_buffer = ""
        ignored_tokens = {"OK", "SEARCHING...", "NO DATA", "STOPPED", "?"}

        def notificaion_handler(sender, data):
            # BLE notifications may arrive in partial chunks.
            # Example chunk sequence:
            #   chunk A: "41 0C 1A"
            #   chunk B: " F8\r010D\r41 0D 28\r>"
            # Combined buffer becomes:
            #   "41 0C 1A F8\r010D\r41 0D 28\r>"
            # Parsed lines:
            #   - "41 0C 1A F8"  -> decoded PID response (RPM)
            #   - "010D"         -> request echo, ignored
            #   - "41 0D 28"     -> decoded PID response (speed)
            
            nonlocal rx_buffer
            chunk = data.decode(errors="ignore")
            debug_log(args.debug, f"RX raw from {sender}: {chunk!r}")
            rx_buffer += chunk
            if ">" in rx_buffer:
                prompt_received.set()

            if "\r" not in rx_buffer and "\n" not in rx_buffer and ">" not in rx_buffer:
                return

            for sep in ("\r", "\n", ">"):
                rx_buffer = rx_buffer.replace(sep, "\n")

            lines = [line.strip() for line in rx_buffer.split("\n")]
            if rx_buffer.endswith("\n"):
                rx_buffer = ""
            else:
                rx_buffer = lines.pop() if lines else ""

            for text in lines:
                if not text:
                    continue

                upper = text.upper()
                compact = upper.replace(" ", "")
                if upper in ignored_tokens or upper.startswith("AT") or upper.startswith("ELM327"):
                    continue
                if len(compact) == 4 and compact.startswith("01") and all(c in "0123456789ABCDEF" for c in compact):
                    continue

                result = decode_response(text)
                if result is not None:
                    dashboard_dataDict[result["pid"]] = result
                    debug_log(args.debug, f"Decoded PID {result['pid']}: {result['value']} {result['unit']}".strip())
                else:
                    debug_log(args.debug, f"Ignored non-PID line: {text}")
        
        # start notifications
        await client.start_notify(rx_uuid, notificaion_handler)
        
        # Send innitalization command
        for cmd in init_commands:
            prompt_received.clear()
            debug_log(args.debug, f"Sending initialization command: {cmd.strip()}")
            await client.write_gatt_char(tx_uuid, cmd.encode())
            try:
                await asyncio.wait_for(prompt_received.wait(), timeout=args.response_timeout)
            except asyncio.TimeoutError:
                debug_log(args.debug, f"Timed out waiting for prompt after initialization command: {cmd.strip()}")
            await asyncio.sleep(init_delay)
        

        try:
            with Live(build_table(dashboard_dataDict), refresh_per_second=4) as live:
                try:                
                    while True:
                        for pid_cmd in PID_LIST:
                            prompt_received.clear()
                            debug_log(args.debug, f"Requesting PID: {pid_cmd}")
                            await client.write_gatt_char(tx_uuid, (pid_cmd + "\r").encode())
                            try:
                                await asyncio.wait_for(prompt_received.wait(), timeout=args.response_timeout)
                            except asyncio.TimeoutError:
                                debug_log(args.debug, f"Timed out waiting for prompt after PID: {pid_cmd}")
                            await asyncio.sleep(poll_delay)
                            live.update(build_table(dashboard_dataDict))
                        await asyncio.sleep(post_cycle_delay)
                except KeyboardInterrupt:
                    pass
        finally:

                # stop notifications
            await client.stop_notify(rx_uuid)

        

   

def cli() -> None:
    try:
        cli_args = parse_args()
        asyncio.run(main(cli_args))
    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    cli()
