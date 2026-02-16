# import asyncio
# import pprint
# from bleak import BleakScanner, BleakClient

# async def main():
#     uuid_batt_char = ""
#     my_device = ''
#     devices = await BleakScanner.discover(5.0, return_adv=True)
#     pprint.pprint(devices)
#     for d in devices:
#         if (devices[d][1].local_name == 'Jesse phone'):
#             print("Found Jesse's phone!")
#             my_device = d
#             print(my_device)
    
#     if not my_device:
#         print("Could not find jesses's phone")
#         return
    
#     address = my_device
#     async with BleakClient(address) as client:
#         print(f"Connected to {address}")
#         for service in client.services:
#             # pprint.pprint(dir(service))
#             for (char) in service.characteristics:
#                 pprint.pprint(f"Characteristic: {char.uuid}, Properties: {char.properties}, Description: {char.description}")
#                 if (char.description == "Battery Level"):
#                     uuid_batt_char = char.uuid
        
#         try:
#             battery_level = await client.read_gatt_char(uuid_batt_char)
#             print(f"Battery level: {int(battery_level[0])}%")
#         except Exception as e:
#             print(f"Error reading battery level: {e}")

# asyncio.run(main())