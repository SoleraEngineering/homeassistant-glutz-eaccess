"""
Glutz eAccess lock platform
"""
from homeassistant.components.lock import LockDevice, SUPPORT_OPEN
from homeassistant.const import (STATE_LOCKED, STATE_UNLOCKED)
from ..glutz.const import DATA_GLUTZ


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    glutz = hass.data[DATA_GLUTZ]

    discovered_entities = await glutz.discover_access_points()

    entities = [GlutzLock(device, glutz) for device in discovered_entities]

    add_entities(entities)


class GlutzLock(LockDevice):
    """Representation of a Glutz eAccess lock."""

    def __init__(self, device, glutz):
        """Initialize the lock."""
        self._name = device['label']
        self._state = self.resolve_state(device.get('state'))
        self._glutz = glutz
        self._id = device['id']


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
        """Do nothing!"""


    async def async_open(self, **kwargs) -> None:
        """Open the door latch."""
        self._state = STATE_UNLOCKED
        self.schedule_update_ha_state()


    async def async_update(self) -> None:
        state = await self._glutz.fetch_access_point_status(self._id)
        self._state = self.resolve_state(state)

        # if state != self._state:
        #    self.schedule_update_ha_state()


    def resolve_state(self, glutz_state):
        if glutz_state == 'unlocked':
            return STATE_UNLOCKED

        return STATE_LOCKED


    @property
    def supported_features(self):
        return SUPPORT_OPEN