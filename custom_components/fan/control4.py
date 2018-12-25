"""
Support for Control4 Fans and Oscillators.
For more details about this platform, please refer to the documentation at
https://github.com/r3pi/homeassistant-glutz/custom_components/fan/
"""
import logging
import voluptuous as vol

from homeassistant.const import (
    CONF_LATITUDE, CONF_LONGITUDE, CONF_DEVICES, CONF_SCAN_INTERVAL
)

from homeassistant.components.fan import (
    ATTR_SPEED, ATTR_OSCILLATING,
    SUPPORT_SET_SPEED, SUPPORT_OSCILLATE,
    SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH,
    FanEntity, PLATFORM_SCHEMA
)

from homeassistant.helpers import config_validation as cv

DATA_CONTROL4 = 'glutz'


_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = ['glutz']

CONF_DESC = 'desc'
CONF_C4ID = 'c4id'
CONF_DIMMABLE = 'dimmable'
CONF_C4VAR_FAN_SPEED = 'c4var_fan_speed'
CONF_C4VAR_STATUS = 'c4var_status'
CONF_TYPE = 'type'

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_C4ID): cv.positive_int,
    vol.Optional(CONF_TYPE, default="fan"): cv.string,
    vol.Optional(CONF_DESC, default=""): cv.string,
    vol.Optional(CONF_LATITUDE, default=0): cv.latitude,
    vol.Optional(CONF_LONGITUDE, default=0): cv.longitude,
    vol.Optional(CONF_DIMMABLE, default=True): cv.boolean,
    vol.Optional(CONF_C4VAR_FAN_SPEED, default=1001): cv.positive_int,
    vol.Optional(CONF_C4VAR_STATUS, default=1000): cv.positive_int,
    vol.Optional(CONF_SCAN_INTERVAL, default=10): vol.All(vol.Coerce(int), vol.Range(min=1))
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_DEVICES, default={}): {cv.string: DEVICE_SCHEMA}
})


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up Control4 fans"""
    _LOGGER.debug('async_setup_platform: %s, %s', str(config), str(discovery_info))

    switch = hass.data[DATA_CONTROL4].control4
    devices = [Control4Fan(device_name, device, switch) for device_name, device in config[CONF_DEVICES].items()]

    async_add_devices(devices, True)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up Control4 fans"""
    _LOGGER.debug('async_setup_entry: %s', str(entry))


FAN_SPEEDS = {
    SPEED_OFF: 0,
    SPEED_LOW: 50,
    SPEED_MEDIUM: 120,
    SPEED_HIGH: 255
}



class Control4Fan(FanEntity):
    """Representation of a Control4 Fan"""

    def __init__(self, device_name, device, switch):
        """Initialize the light"""
        _LOGGER.debug('Init fan: %s', str(device))
        self._name = device_name
        self._c4id = device['c4id']
        self._desc = device['desc']
        self._latitude = device['latitude']
        self._longitude = device['longitude']
        self._dimmable = device['dimmable']
        self._c4var_fan_speed = device['c4var_fan_speed']
        self._c4var_status = device['c4var_status']
        self._type = device['type']

        self._switch = switch
        self._state = False
        self._fan_speed = None

        self._assumed_state = False
        self._available = True

        self.oscillating = None
        self.direction = None

    @property
    def unique_id(self) -> str:
        """Return the ID of this fan."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Return true if fan is on."""
        return self._state

    @property
    def speed(self):
        return self._fan_speed

    @property
    def speed_list(self):
        if self._type == 'fan':
            return [SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH]

        return []

    @property
    def supported_features(self) -> int:
        if self._type == 'oscillator':
            return SUPPORT_OSCILLATE

        if self._dimmable is True:
            return SUPPORT_SET_SPEED

        return 0

    @property
    def assumed_state(self) -> bool:
        """We can read the actual state."""
        return self._assumed_state

    @property
    def available(self) -> bool:
        return self._available

    def c4_to_ha_speed(self, c4_speed):
        target_speed = SPEED_OFF
        speed_difference = 100000

        for attr, value in FAN_SPEEDS.items():
            diff = abs(c4_speed - value)

            if diff < speed_difference:
                speed_difference = diff
                target_speed = attr

        return target_speed

    def ha_to_c4_speed(self, ha_speed):
        return FAN_SPEEDS[ha_speed]

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the fan control device on"""
        _LOGGER.debug("turn_on: %s", self._name)

        await self._switch.on(self._c4id)
        self._state = True

        ha_fan_speed = kwargs.get(ATTR_SPEED)

        if ha_fan_speed is not None:
            c4_fan_speed = self.ha_to_c4_speed(ha_fan_speed)
            _LOGGER.debug('set fan speed: %d, %s', c4_fan_speed, ha_fan_speed)
            await self._switch.set_level(self._c4id, c4_fan_speed)
            self._fan_speed = ha_fan_speed

        if self._type == 'oscillator':
            self.oscillating = True

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off"""
        _LOGGER.debug("turn_off: %s", self._name)

        await self._switch.off(self._c4id)

        self._state = False

        if self._type == 'oscillator':
            self.oscillating = False

    async def async_update(self) -> None:
        """Synchronize internal state with the actual device state."""
        _LOGGER.debug("update: %s", self._name)

        self._state = bool(int(await self._switch.get(self._c4id, self._c4var_status)))

        if self._dimmable is True:
            c4_fan_speed = int(await self._switch.get(self._c4id, self._c4var_fan_speed))
            ha_fan_speed = self.c4_to_ha_speed(c4_fan_speed)

            _LOGGER.debug('get fan speed: %f, %s', c4_fan_speed, ha_fan_speed)

            self._fan_speed = ha_fan_speed

            if ha_fan_speed == SPEED_OFF:
                self._state = False

        if self._type == 'oscillator':
            self.oscillating = self._state

        _LOGGER.debug("status: %s, %d, %s", self._name, self._state, self._fan_speed)

    async def async_oscillate(self, oscillating: bool) -> None:
        _LOGGER.debug("oscillate: ", self._name)

        if oscillating:
            await self.async_turn_on()
        else:
            await self.async_turn_off()

        self.oscillating = oscillating

