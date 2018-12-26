"""
Glutz eAccess lock platform
"""
from homeassistant.components.lock import LockDevice, SUPPORT_OPEN
from homeassistant.const import (STATE_LOCKED, STATE_UNLOCKED)
from ..glutz.const import DATA_GLUTZ

import logging
import re

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    _LOGGER.debug('async_setup_platform')

    glutz = hass.data[DATA_GLUTZ]

    discovered_entities = await glutz.discover_access_points()

    entities = [GlutzLock(device, glutz) for device in discovered_entities]

    add_entities(entities)


class GlutzLock(LockDevice):
    """Representation of a Glutz eAccess lock."""

    def __init__(self, device, glutz):
        """Initialize the lock."""
        _LOGGER.debug("Instantiating lock: %s", str(device))

        self._name = self.get_safe_device_name(device.get('label', ''))
        self._state = self.resolve_state(device.get('state'))
        self._glutz = glutz
        self._id = device.get('id')


    @property
    def should_poll(self):
        return True


    @property
    def name(self):
        """Return the name of the lock if any."""
        return self._name


    @property
    def is_locked(self):
        """Return true if lock is locked."""
        return self._state == STATE_LOCKED


    async def async_lock(self, **kwargs) -> None:
        """Lock the device."""
        """Do nothing!"""


    async def async_unlock(self, **kwargs) -> None:
        """Unlock the device."""
        await self.async_open(**kwargs)


    async def async_open(self, **kwargs) -> None:
        """Open the door latch."""
        result = await self._glutz.open_access_point(self._id)

        if result is True:
            self._state = STATE_UNLOCKED
        else:
            self._state = STATE_LOCKED

        # self.schedule_update_ha_state()


    async def async_update(self) -> None:
        state = await self._glutz.fetch_access_point_status(self._id)
        self._state = self.resolve_state(state)

        # if state != self._state:
        #    self.schedule_update_ha_state()


    def resolve_state(self, glutz_state):
        if glutz_state == 'unlocked':
            return STATE_UNLOCKED

        return STATE_LOCKED

    def get_safe_device_name(self, label):
        return re.sub(r'[^a-z0-9]', '_', label.lower())

    @property
    def supported_features(self):
        return SUPPORT_OPEN
