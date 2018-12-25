"""
Support for Glutz eAccess access points
"""
import logging
import voluptuous as vol

from homeassistant.const import (
    CONF_LATITUDE, CONF_LONGITUDE, CONF_DEVICES, CONF_SCAN_INTERVAL
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, Light, PLATFORM_SCHEMA
)

from homeassistant.helpers import config_validation as cv

DATA_CONTROL4 = 'glutz'


_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = ['glutz']

CONF_DESC = 'desc'
CONF_C4ID = 'c4id'
CONF_DIMMABLE = 'dimmable'
CONF_C4VAR_BRIGHTNESS = 'c4var_brightness'
CONF_C4VAR_STATUS = 'c4var_status'

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_C4ID): cv.positive_int,
    vol.Optional(CONF_DESC, default=""): cv.string,
    vol.Optional(CONF_LATITUDE, default=0): cv.latitude,
    vol.Optional(CONF_LONGITUDE, default=0): cv.longitude,
    vol.Optional(CONF_DIMMABLE, default=True): cv.boolean,
    vol.Optional(CONF_C4VAR_BRIGHTNESS, default=1001): cv.positive_int,
    vol.Optional(CONF_C4VAR_STATUS, default=1000): cv.positive_int,
    vol.Optional(CONF_SCAN_INTERVAL, default=10): vol.All(vol.Coerce(int), vol.Range(min=1))
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_DEVICES, default={}): {cv.string: DEVICE_SCHEMA}
})


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up Control4 lights"""
    _LOGGER.debug('async_setup_platform: %s, %s', str(config), str(discovery_info))

    switch = hass.data[DATA_CONTROL4].control4
    lights = [Control4Light(device_name, device, switch) for device_name, device in config[CONF_DEVICES].items()]

    async_add_devices(lights, True)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up Control4 lights"""
    _LOGGER.debug('async_setup_entry: %s', str(entry))


class Control4Light(Light):
    """Representation of a Control4 Light"""

    def __init__(self, device_name, device, switch):
        """Initialize the light"""
        _LOGGER.debug('Init light: %s', str(device))
        self._name = device_name
        self._c4id = device['c4id']
        self._desc = device['desc']
        self._latitude = device['latitude']
        self._longitude = device['longitude']
        self._dimmable = device['dimmable']
        self._c4var_brightness = device['c4var_brightness']
        self._c4var_status = device['c4var_status']

        self._switch = switch
        self._state = False
        self._brightness = 0

        self._assumed_state = False
        self._available = True

    @property
    def unique_id(self) -> str:
        """Return the ID of this light."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._state

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        if self._dimmable is True:
            return SUPPORT_BRIGHTNESS
        return 0

    @property
    def assumed_state(self) -> bool:
        """We can read the actual state."""
        return self._assumed_state

    @property
    def available(self) -> bool:
        return self._available

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on"""
        _LOGGER.debug("turn_on: %s", self._name)

        await self._switch.on(self._c4id)
        self._state = True

        ha_brightness = kwargs.get(ATTR_BRIGHTNESS)

        if ha_brightness is not None:
            c4_brightness = int(ha_brightness / 2.55)
            _LOGGER.debug('set brightness: %d, %d', c4_brightness, ha_brightness)
            await self._switch.set_level(self._c4id, c4_brightness)
            self._brightness = ha_brightness

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off"""
        _LOGGER.debug("turn_off: %s", self._name)

        await self._switch.off(self._c4id)

        self._state = False

    async def async_update(self) -> None:
        """Synchronize internal state with the actual light state."""
        _LOGGER.debug("update: %s", self._name)

        self._state = bool(int(await self._switch.get(self._c4id, self._c4var_status)))

        if self._dimmable is True:
            c4_brightness = int(await self._switch.get(self._c4id, self._c4var_brightness))
            ha_brightness = int(float(c4_brightness * 2.55))

            _LOGGER.debug('get brightness: %f, %d', c4_brightness, ha_brightness)

            self._brightness = ha_brightness

            if ha_brightness == 0:
                self._state = False

        _LOGGER.debug("status: %s, %d, %d", self._name, self._state, self._brightness)
