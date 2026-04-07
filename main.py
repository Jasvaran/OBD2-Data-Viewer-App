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
        help="seconds to wait after each PID request before sending the next one",
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

    args = parser.parse_args()

    if args.simulate and (args.device_name or args.device_address):
        parser.error("--simulate cannot be combined with --device-name or --device-address")

    return args


def debug_log(enabled: bool, message: str) -> None:
    if enabled:
        print(f"[debug] {message}")


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
    from bleak import BleakClient
    from rich.live import Live

    from dashboard import build_table
    from dashboard import dashboard_dataDict

    simulation_on = args.simulate
    init_delay = 0.2 if simulation_on else 1.0
    poll_delay = args.poll_delay if args.poll_delay is not None else (0.2 if simulation_on else 0.15)
    post_cycle_delay = 0.1 if simulation_on else 0.15
    tx_uuid = None
    rx_uuid = None

    if simulation_on:
        print("Running in simulation mode. Using MockBleakClient.")
        address = "SIMULATED"
    else:
        address = await select_device(args)
        if address is None:
            return

    ClientClass = MockBleakClient if simulation_on else BleakClient


    async with ClientClass(address) as client:
        print(f"Connected to {address}")

        for service in client.services:
            for char in service.characteristics:
                props = char.properties
                if ("write" in props or "write-without-response" in props) and tx_uuid is None:
                    tx_uuid = char.uuid
                if ("notify" in props or "indicate" in props) and rx_uuid is None:
                    rx_uuid = char.uuid
                debug_log(
                    args.debug,
                    f"Characteristic: {char.uuid}, Properties: {char.properties}, Description: {char.description}",
                )

        if tx_uuid is None or rx_uuid is None:
            print("Could not determine TX/RX BLE characteristics for the selected device.")
            return

        debug_log(args.debug, f"TX_UUID: {tx_uuid}")
        debug_log(args.debug, f"RX_UUID: {rx_uuid}")

        # Notification handler function
        rx_buffer = ""
        ignored_tokens = {"OK", "SEARCHING...", "NO DATA", "?"}

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
            rx_buffer += data.decode(errors="ignore")

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
                else:
                    debug_log(args.debug, f"Ignored non-PID line: {text}")
        
        # start notifications
        await client.start_notify(rx_uuid, notificaion_handler)
        
        # Send innitalization command
        for cmd in init_commands:
            debug_log(args.debug, f"Sending initialization command: {cmd.strip()}")
            await client.write_gatt_char(tx_uuid, cmd.encode())
            await asyncio.sleep(init_delay)  # wait for response 
        

        try:
            with Live(build_table(dashboard_dataDict), refresh_per_second=4) as live:
                try:                
                    while True:
                        for pid_cmd in PID_LIST:
                            debug_log(args.debug, f"Requesting PID: {pid_cmd}")
                            await client.write_gatt_char(tx_uuid, (pid_cmd + "\r").encode())
                            await asyncio.sleep(poll_delay)  # wait for response
                            live.update(build_table(dashboard_dataDict))
                        await asyncio.sleep(post_cycle_delay)
                except KeyboardInterrupt:
                    pass
        finally:

                # stop notifications
            await client.stop_notify(rx_uuid)

        

   

if __name__ == "__main__":
    try:
        cli_args = parse_args()
        asyncio.run(main(cli_args))
    except KeyboardInterrupt:
        print("\nStopped by user.")
