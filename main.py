import asyncio
import pprint
from bleak import BleakScanner, BleakClient
from obd2_simulator import MockBleakClient
from intialization_commands import init_commands
from PID_Resources import decode_response
from PID_Resources import PID_LIST
from dashboard import dashboard_dataDict
from rich.live import Live
from dashboard import build_table
async def main():

    simulation_on = False
    init_delay = 0.2 if simulation_on else 1.0
    poll_delay = 0.2 if simulation_on else 0.15
    post_cycle_delay = 0.1 if simulation_on else 0.15
    device_dict = {}
    TX_UUID = None
    RX_UUID = None
    my_device = None

    if simulation_on:
        print("Running in simulation mode. Using MockBleakClient.")
        address = "SIMULATED"
    else:
        print("Running in real mode. Using actual BleakClient.")
        devices = await BleakScanner.discover(5.0, return_adv=True)

        named_devices = []
        for address, (_, adv_data) in devices.items():
            local_name = adv_data.local_name if adv_data is not None else None
            if local_name:
                named_devices.append((address, local_name))

        if not named_devices:
            print("No named BLE devices were found. Try scanning again.")
            return

        for i, (address, local_name) in enumerate(named_devices):
            device_dict[i] = {"address": address, "name": local_name}

        pprint.pprint({i: device_dict[i]["name"] for i in device_dict})

        select = input("Enter the number corresponding to the device you want to connect to: ")
        try:
            select = int(select)
            if select in device_dict:
                print(f"Selected device: {device_dict[select]['name']}")
                my_device = device_dict[select]["address"]
            else:
                print("Invalid selection. Exiting.")
                return
        except ValueError:
            print("Invalid input. Please enter a number. Exiting.")
            return
        
        address = my_device
        print(address)
    
    ClientClass = MockBleakClient if simulation_on else BleakClient


    async with ClientClass(address) as client:
        print(f"Connected to {address}")

        for service in client.services:
            for char in service.characteristics:
                props = char.properties
                if ("write" in props or "write-without-response" in props) and TX_UUID is None:
                    TX_UUID = char.uuid
                if ("notify" in props or "indicate" in props) and RX_UUID is None:
                    RX_UUID = char.uuid
                pprint.pprint(f"Characteristic: {char.uuid}, Properties: {char.properties}, Description: {char.description}")
        print(f"TX_UUID: {TX_UUID}")
        print(f"RX_UUID: {RX_UUID}")

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
                    print(f"Ignored non-PID line: {text}")
        
        # start notifications
        await client.start_notify(RX_UUID, notificaion_handler)
        
        # Send innitalization command
        for cmd in init_commands:
            print(f"Sending initialization command: {cmd.strip()}")
            await client.write_gatt_char(TX_UUID, cmd.encode())
            await asyncio.sleep(init_delay)  # wait for response 
        

        try:
            with Live(build_table(dashboard_dataDict), refresh_per_second=4) as live:
                try:                
                    while True:
                        for pid_cmd in PID_LIST:
                            # print(f"Requesting PID: {pid_cmd}")
                            await client.write_gatt_char(TX_UUID, (pid_cmd + "\r").encode())
                            await asyncio.sleep(poll_delay)  # wait for response
                            live.update(build_table(dashboard_dataDict))
                        await asyncio.sleep(post_cycle_delay)
                except KeyboardInterrupt:
                    pass
        finally:

                # stop notifications
            await client.stop_notify(RX_UUID)

        

   

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")