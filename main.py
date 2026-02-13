import asyncio
from bleak import BleakScanner, BleakClient

async def main():
    devices = await BleakScanner.discover(10.0, return_adv=True)
    for i, d in enumerate(devices):
        adv_data = devices[d][1]
        print(f"{i}: {adv_data}")
        address = d.address if hasattr(d, "address") else d
        try:
            async with BleakClient(address) as client:
                print(f"Connected to {address}")
                for service in client.services:
                    print(f"  Service: {service.uuid}")
                    for char in service.characteristics:
                        print(f"    Characteristic: {char.uuid}, properties: {char.properties}")
        except Exception as e:
            print(f"Could not connect to {address}: {e}")

asyncio.run(main())