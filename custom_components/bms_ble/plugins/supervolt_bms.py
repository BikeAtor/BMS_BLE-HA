"""Module to support Supervolt BMS (Black Battery)."""

import sys
import asyncio
from collections.abc import Callable
import logging
from typing import Any, Final
import time

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak.uuids import normalize_uuid_str

from ..const import (
    ATTR_BATTERY_CHARGING,
    ATTR_BATTERY_LEVEL,
    ATTR_CURRENT,
    ATTR_CYCLE_CAP,
    # ATTR_CYCLE_CHRG,
    # ATTR_CYCLES,
    ATTR_DELTA_VOLTAGE,
    ATTR_POWER,
    # ATTR_RUNTIME,
    ATTR_TEMPERATURE,
    ATTR_VOLTAGE,
    ATTR_CELL_VOLTAGES,
    KEY_CELL_VOLTAGE,
    KEY_CELL_COUNT
)
from .basebms import BaseBMS, BMSsample

BAT_TIMEOUT: Final = 10
MAX_TIME_S: Final = 120

LOGGER = logging.getLogger(__name__)

UUID_TX: Final = normalize_uuid_str("ff02")
UUID_SERVICE: Final = normalize_uuid_str("ff00")

class SupervoltData:
    cellV = None
    totalV = None
    soc = None
    workingState = None
    alarm = None
    chargingA = None
    dischargingA = None
    loadA = None
    tempC = None
    completeAh = None
    remainingAh = None
    designedAh = None
    verbose = False


    # time of data changed
    lastUpdatetime = time.time()

    def __init__(self) -> None:
        self.tempC = [None, None, None, None]
        self.cellV = [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]

    def parse(self, data: bytearray):
        try:
            if data:
                if self.verbose:
                    LOGGER.debug("parse data: {}".format(type(data)))
                if len(data) == 128:
                    if self.verbose:
                        LOGGER.debug("parse Realtimedata: {}".format(type(data)))
                    if type(data) is bytearray: 
                        data = bytes(data)
                    if type(data) is bytes:
                        # print("bytes")
                    
                        start = 1
                        end = start + 2
                        self.address = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("address: " + str(self.address))
                        
                        start = end
                        end = start + 2
                        self.command = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("command: " + str(self.command))
                        
                        start = end
                        end = start + 2
                        self.version = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("version: " + str(self.version))
                        
                        start = end
                        end = start + 4
                        self.length = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("length: " + str(self.length))
                        
                        start = end
                        end = start + 14
                        bdate = data[start: end]
                        if self.verbose:
                            LOGGER.debug("date: " + str(bdate))
                    
                        start = end
                        end = start + 16 * 4
                        bvoltarray = data[start: end]
                        # print("voltarray: " + str(bvoltarray))
                        self.totalV = 0
                        if self.cellV:
                            for i in range(0, 11):
                                bvolt = data[(start + i * 4): (start + i * 4 + 4)]
                                self.cellV[i] = int(bvolt.decode(), 16) / 1000.0
                                self.totalV += self.cellV[i]
                                if self.verbose:
                                    LOGGER.debug("volt" + str(i) + ": " + str(bvolt) + " / " + str(self.cellV[i]) + "V")
                        
                        if self.verbose:
                            LOGGER.debug("totalVolt: " + str(self.totalV))
                        
                        start = end
                        end = start + 4
                        bcharging = data[start: end]
                        self.chargingA = int(bcharging.decode(), 16) / 100.0
                        if self.verbose:
                            LOGGER.debug("charching: " + str(bcharging) + " / " + str(self.chargingA) + "A")
                        if self.chargingA > 500:
                            # problem with supervolt
                            LOGGER.info("charging too big: {}".format(self.chargingA))
                            self.chargingA = 0.0
                            
                        start = end
                        end = start + 4
                        bdischarging = data[start: end]
                        self.dischargingA = int(bdischarging.decode(), 16) / 100.0
                        if self.verbose:
                            LOGGER.debug("discharching: " + str(bdischarging) + " / " + str(self.dischargingA) + "A")
                        if self.dischargingA > 500:
                            # problem with supervolt
                            LOGGER.info("discharging too big: {}".format(self.dischargingA))
                            self.dischargingA = 0.0
                        
                        self.loadA = -self.chargingA + self.dischargingA
                        
                        for i in range(0, 4):
                            start = end
                            end = start + 2
                            if self.tempC:
                                btemp = data[start: end]
                                self.tempC[i] = int(btemp.decode(), 16) - 40
                                if self.verbose:
                                    LOGGER.debug("temp" + str(i) + ": " + str(btemp) + " / " + str(self.tempC[i]) + "°C")
                        
                        start = end
                        end = start + 4
                        self.workingState = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("workingstate: " + str(self.workingState) + " / " + str(data[start: end])
                            +" / " + self.getWorkingStateTextShort() + " / " + self.getWorkingStateText())
                        
                        start = end
                        end = start + 2
                        self.alarm = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("alarm: " + str(self.alarm))
                        
                        start = end
                        end = start + 4
                        self.balanceState = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("balanceState: " + str(self.balanceState))
                        
                        start = end
                        end = start + 4
                        self.dischargeNumber = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("dischargeNumber: " + str(self.dischargeNumber))
                            
                        start = end
                        end = start + 4
                        self.chargeNumber = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("chargeNumber: " + str(self.chargeNumber))
                        
                        # State of Charge (%)
                        start = end
                        end = start + 2
                        self.soc = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("soc: " + str(self.soc))
                            LOGGER.info("end of parse realtimedata")
                        self.lastUpdatetime = time.time()
                    else:
                        LOGGER.warning("no bytes")
                elif len(data) == 30:
                    if self.verbose:
                        LOGGER.debug("capacity")
                    if type(data) is bytearray: 
                        data = bytes(data)
                    if type(data) is bytes:
                        start = 1
                        end = start + 2
                        self.address = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("address: " + str(self.address))
                        
                        start = end
                        end = start + 2
                        self.command = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("command: " + str(self.command))
                        
                        start = end
                        end = start + 2
                        self.version = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("version: " + str(self.version))
                        
                        start = end
                        end = start + 4
                        self.length = int(data[start: end].decode(), 16)
                        if self.verbose:
                            LOGGER.debug("length: " + str(self.length))
                        
                        start = end
                        end = start + 4
                        breseved = data[start: end]
                        if self.verbose:
                            LOGGER.debug("reseved: " + str(breseved))
                        
                        start = end
                        end = start + 4
                        self.remainingAh = int(data[start: end].decode(), 16) / 10.0
                        if self.verbose:
                            LOGGER.debug("remainingAh: " + str(self.remainingAh) + " / " + str(data[start: end]))
                        
                        start = end
                        end = start + 4
                        self.completeAh = int(data[start: end].decode(), 16) / 10.0
                        if self.verbose:
                            LOGGER.debug("completeAh: " + str(self.completeAh))
                        
                        start = end
                        end = start + 4
                        self.designedAh = int(data[start: end].decode(), 16) / 10.0
                        if self.verbose:
                            LOGGER.debug("designedAh: " + str(self.designedAh))
                            LOGGER.info("end of parse capacity")
                        self.lastUpdatetime = time.time()
                        
                else:
                    LOGGER.warning("wrong length: " + str(len(data)))
            else:
                LOGGER.debug("no data")
        except:
            LOGGER.error(sys.exc_info(), exc_info=True)

    def getData(self):
        if (time.time() - self.lastUpdatetime) > MAX_TIME_S or not self.totalV:
            # data is old
            LOGGER.debug("data too old")
            return None
        data = {
            ATTR_VOLTAGE: self.totalV,
            ATTR_DELTA_VOLTAGE: self.totalV,
            ATTR_CURRENT: self.loadA,
            ATTR_BATTERY_LEVEL: self.soc,
            #ATTR_POWER: (self.totalV * self.loadA),
            ATTR_CYCLE_CAP: self.remainingAh,
            KEY_CELL_COUNT: 4
        }  # set fixed values for dummy battery
        if self.tempC:
            data |= {
                ATTR_TEMPERATURE: self.tempC[0]
            }
        for i in range(0,4):
            data |= {f"{KEY_CELL_VOLTAGE}{i+1}": self.cellV[i]}
        data |= {ATTR_CELL_VOLTAGES: [
                    v
                    for k, v in data.items()
                    if k.startswith(KEY_CELL_VOLTAGE)
                ]}

        return data

    def resetValues(self):
        try:
            LOGGER.info("reset")
            self.alarm = None
            self.balanceState = None
            if self.cellV:
                for i in range(0, 11):
                    self.cellV[i] = None
            self.chargeNumber = None
            self.chargingA = None
            self.completeAh = None
            self.designedAh = None
            self.dischargeNumber = None
            self.dischargingA = None
            self.loadA = None
            self.remainingAh = None
            self.soc = None
            if self.tempC:
                for i in range(0, 4):
                    self.tempC[i] = None
            self.totalV = None
            self.version = None
            self.workingState = None
        except:
            LOGGER.error(sys.exc_info(), exc_info=True)

    def getWorkingStateTextShort(self):
        if self.workingState is None:
            return "nicht erreichbar"
        if self.workingState & 0xF003 >= 0xF000:
            return "Normal"
        if self.workingState & 0x000C > 0x0000:
            return "Schutzschaltung"
        if self.workingState & 0x0020 > 0:
            return "Kurzschluss"
        if self.workingState & 0x0500 > 0:
            return "Überhitzt"
        if self.workingState & 0x0A00 > 0:
            return "Unterkühlt"
        return "Unbekannt"

    def getWorkingStateText(self):
        text = ""
        if self.workingState is None:
            return "Unbekannt"
        if self.workingState & 0x0001 > 0:
            text = self.appendState(text, "Laden")
        if self.workingState & 0x0002 > 0:
            text = self.appendState(text , "Entladen")
        if self.workingState & 0x0004 > 0:
            text = self.appendState(text , "Überladungsschutz")
        if self.workingState & 0x0008 > 0:
            text = self.appendState(text , "Entladeschutz")
        if self.workingState & 0x0010 > 0:
            text = self.appendState(text , "Überladen")
        if self.workingState & 0x0020 > 0:
            text = self.appendState(text , "Kurzschluss")
        if self.workingState & 0x0040 > 0:
            text = self.appendState(text , "Entladeschutz 1")
        if self.workingState & 0x0080 > 0:
            text = self.appendState(text , "Entladeschutz 2")
        if self.workingState & 0x0100 > 0:
            text = self.appendState(text , "Überhitzt (Laden)")
        if self.workingState & 0x0200 > 0:
            text = self.appendState(text , "Unterkühlt (Laden)")
        if self.workingState & 0x0400 > 0:
            text = self.appendState(text , "Überhitzt (Entladen)")
        if self.workingState & 0x0800 > 0:
            text = self.appendState(text , "Unterkühlt (Entladen)")
        if self.workingState & 0x1000 > 0:
            text = self.appendState(text , "DFET an")
        if self.workingState & 0x2000 > 0:
            text = self.appendState(text , "CFET an")
        if self.workingState & 0x4000 > 0:
            text = self.appendState(text , "DFET Schalter an")
        if self.workingState & 0x8000 > 0:
            text = self.appendState(text , "CFET Schalter an")
        
        return text

    def appendState(self, text, append):
        if text is None  or len(text) == 0:
            return append
        return text + " | " + append

class BMS(BaseBMS):
    """Supervolt battery class implementation."""
    supervoltDatas = {}
    supervoltData: SupervoltData = None

    def __init__(self, ble_device: BLEDevice, reconnect: bool = False) -> None:
        """Initialize BMS."""
        LOGGER.debug("%s init(), BT address: %s", self.device_id(), ble_device.address)
        self._reconnect: Final[bool] = reconnect
        self._ble_device = ble_device
        assert self._ble_device.name is not None
        self._client: BleakClient | None = None
        self._data_event = asyncio.Event()
        # store old data, cause connection sometime fails
        self.supervoltData = self.supervoltDatas.get(self._ble_device.name , SupervoltData())

    @staticmethod
    def matcher_dict_list() -> list[dict[str, Any]]:
        """Provide BluetoothMatcher definition."""
        return [{"local_name": "libatt*", "connectable": True}]

    @staticmethod
    def device_info() -> dict[str, str]:
        """Return device information for the battery management system."""
        return {"manufacturer": "Supervolt", "model": "Black"}

    async def _connect(self) -> None:
        """Connect to the BMS and setup notification if not connected."""

        if self._client is None:
                self._client = BleakClient(
                    self._ble_device,
                    disconnected_callback=self._on_disconnect,
                    services=[UUID_SERVICE],
                )
        if not self._client.is_connected:
            LOGGER.debug("Connecting BMS (%s)", self._ble_device.name)
            await self._client.connect()
            await self._client.start_notify("6e400003-b5a3-f393-e0a9-e50e24dcca9e", self._notification_handler)
            LOGGER.debug("notify started")
        else:
            LOGGER.debug("BMS %s already connected", self._ble_device.name)

    def _notification_handler(self, _sender, data: bytearray) -> None:
        LOGGER.debug(
            "(%s) Rx BLE data: %s %s",
            self._ble_device.name,
            len(data),
            data
        )
        self.supervoltData.parse(data)

        self._data_event.set()

    async def _wait_event(self) -> None:
        await self._data_event.wait()
        self._data_event.clear()

    async def disconnect(self) -> None:
        """Disconnect connection to BMS if active."""
        if self._client and self._client.is_connected:
            LOGGER.debug("Disconnecting BMS (%s)", self._ble_device.name)
            try:
                self._data_event.clear()
                # stop notify
                await self._client.stop_notify("6e400003-b5a3-f393-e0a9-e50e24dcca9e")
                await self._client.disconnect()
            except BleakError:
                LOGGER.warning("Disconnect failed!")

    def _on_disconnect(self, _client: BleakClient) -> None:
        """Disconnect callback function."""
        LOGGER.debug("Disconnected from BMS (%s)", self._ble_device.name)

    async def async_update(self) -> BMSsample:
        """Update battery status information."""
        try:
            await self._connect()
            if self._client:
                # connection established
                self.supervoltData.resetValues()

                data = bytes(":000250000E03~", "ascii")
                handle = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
                await self._client.write_gatt_char(char_specifier=handle, data=data)
                await asyncio.wait_for(self._wait_event(), timeout=BAT_TIMEOUT)

                data = bytes(":001031000E05~", "ascii")
                handle = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
                await self._client.write_gatt_char(char_specifier=handle, data=data)
                await asyncio.wait_for(self._wait_event(), timeout=BAT_TIMEOUT)
                await self.disconnect()
        except:
            LOGGER.error(sys.exc_info(), exc_info=True)    

        data = self.supervoltData.getData()
        assert data is not None
        self.calc_values(
            data,
            {
                ATTR_POWER,
                ATTR_BATTERY_CHARGING,
                #ATTR_CYCLE_CAP,
                #ATTR_RUNTIME,
                ATTR_DELTA_VOLTAGE,
                #ATTR_TEMPERATURE,
            },
        )
        
        return data
