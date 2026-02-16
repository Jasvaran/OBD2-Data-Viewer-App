import asyncio
import pprint
from bleak import BleakScanner, BleakClient

async def main():

    simulation_on = False
    device_dict = {}
    TX_UUID = None
    RX_UUID = None
    my_device = None
    devices = await BleakScanner.discover(5.0, return_adv=True)

    for i, d in enumerate(devices):
        device_dict[i] = devices[d][1].local_name
    #     if devices[d][1].local_name == 'IOS-Vlink':
    #         print("Found Vlink OBD2!")
    #         my_device = d
    #         print(my_device)
    #         break
    
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
    # if not my_device:
    #     print("Could not find Vlink OBD2")
    #     return
    
    address = my_device
    print(address)


    async with BleakClient(address) as client:
        print(f"Connected to {address}")

        if simulation_on == True:
            TX_UUID = "12345678-1234-1234-1234-1234567890ac"
            RX_UUID = "12345678-1234-1234-1234-1234567890ad"
            print(f"TX_UUID: {TX_UUID}")
            print(f"RX_UUID: {RX_UUID}")
        else:
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
        init_command = "ATZ\r"
        await client.write_gatt_char(TX_UUID, init_command.encode())

        # wait for response
        await asyncio.sleep(3)

        print("Sending OBD2 command to read coolant temperature...")
        await client.write_gatt_char(TX_UUID, "0105\r".encode())
        
        await asyncio.sleep(3)
        # stop notifications
        await client.stop_notify(RX_UUID)

        

   

asyncio.run(main())