import asyncio
from bluez_peripheral.gatt.service import Service
from bluez_peripheral.gatt.characteristic import characteristic, CharacteristicFlags
from bluez_peripheral.util import get_message_bus
from bluez_peripheral.advert import Advertisement
from bluez_peripheral.util import Adapter

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
TX_UUID = "12345678-1234-5678-1234-56789abcdef1"
RX_UUID = "12345678-1234-5678-1234-56789abcdef2"

class FakeOBDService(Service):
    def __init__(self):
        super().__init__(SERVICE_UUID)

    @characteristic(TX_UUID, CharacteristicFlags.WRITE)
    def tx(self, value, options):
        cmd = bytes(value).decode().strip()
        print("[SIM] Received:", cmd)

        if cmd == "ATZ":
            return b"ELM327 v2.1\r>"
        if cmd == "0105":
            return b"41 05 7B\r>"
        return b"OK\r>"

    @characteristic(RX_UUID, CharacteristicFlags.NOTIFY)
    def rx(self, options):
        return b""

async def run():
    bus = await get_message_bus()
    service = FakeOBDService()
    await service.register(bus)

    adapter = await Adapter.get_first(bus)
    advert = Advertisement("FakeOBD-II", [SERVICE_UUID], 0x0340, 60)
    await advert.register(bus, adapter)

    print("[SIM] BLE Simulator running...")
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run())
