import asyncio
import pprint
from bleak import BleakScanner, BleakClient
from obd2_simulator import MockBleakClient
from intialization_commands import init_commands

async def main():

    simulation_on = True
    delay = 0.2 if simulation_on else 3
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

        for i, d in enumerate(devices):
            device_dict[i] = devices[d][1].local_name
        
        pprint.pprint(device_dict)
        
        select = input("Enter the number corresponding to the device you want to connect to: ")
        try:
            select = int(select)
            if select in device_dict:
                print(f"Selected device: {device_dict[select]}")
                my_device = list(devices.keys())[select]
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
        def notificaion_handler(sender, data):
            print(f"Notification from {sender}: {data.decode(errors='ignore')}")
        
        # start notifications
        await client.start_notify(RX_UUID, notificaion_handler)
        
        # Send innitalization command
        for cmd in init_commands:
            print(f"Sending initialization command: {cmd.strip()}")
            await client.write_gatt_char(TX_UUID, cmd.encode())
            await asyncio.sleep(delay)  # wait for response 


        # wait for response
        await asyncio.sleep(delay)
        print("Sending OBD2 command to read coolant temperature...")
        await client.write_gatt_char(TX_UUID, "0105\r".encode())
        
        await asyncio.sleep(delay)
        # stop notifications
        await client.stop_notify(RX_UUID)

        

   

asyncio.run(main())