"""
Support for devices managed by Glutz eAccess Server
"""

import logging
import voluptuous as vol

import aiohttp
import time
import asyncio
import traceback

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.discovery import async_load_platform

# from homeassistant import config_entries

from .const import DOMAIN, CONF_URL, CONF_PROXY, DATA_GLUTZ_CONFIG, DATA_GLUTZ, CONF_USERNAME, CONF_PASSWORD

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_URL): cv.url,
        vol.Optional(CONF_PROXY, default=None): cv.url,
        vol.Optional(CONF_USERNAME, default=None): cv.string,
        vol.Optional(CONF_PASSWORD, default=None): cv.string
    })
}, extra=vol.ALLOW_EXTRA)



async def async_setup(hass, config):
    """Setup Glutz eAccess Controller"""

    _LOGGER.debug('async_setup')

    if DOMAIN not in config:
        return

    _LOGGER.debug('async_setup has config')

    conf = config[DOMAIN]
    hass.data[DATA_GLUTZ_CONFIG] = conf

    glutz = GlutzController(hass, conf)
    hass.data[DATA_GLUTZ] = glutz

    for component in ['lock']:
        _LOGGER.debug('load_platform: %s', component)
        await async_load_platform(hass, component, DOMAIN, None, config)

    return True


# async def async_setup_entry(hass, entry):
#    _LOGGER.debug('async_setup_entry');
#
#    conf = hass.data[DATA_GLUTZ_CONFIG];
#
#    for component in 'lock':
#        _LOGGER.debug('forward_entry_setup: %s', component)
#        hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, component))
#
#
# config_entry_flow.register_discovery_flow(
#    DOMAIN, 'Glutz', _async_has_devices, config_entries.CONN_CLASS_LOCAL_PUSH)



class GlutzRetryError(TimeoutError):
    pass


class GlutzTimeoutError(TimeoutError):
    pass


def retry(times=20, timeout_secs=10):
    def func_wrapper(f):
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()

            for t in range(times):
                try:
                    self._stats['requests'] += 1
                    return await f(self, *args, **kwargs)
                except (aiohttp.ClientError, ConnectionError) as exc:
                    self._stats['errors'] += 1

                    _LOGGER.debug('Glutz error: %s, %s', str(exc), repr(traceback.format_exc()))

                    # if isinstance(exc, aiohttp.ClientResponseError):
                    traceback.print_exc()

                    if timeout_secs is not None:
                        if time.time() - start_time > timeout_secs:
                            raise GlutzTimeoutError()

                    await asyncio.sleep(0.1 * t)

            raise GlutzRetryError
        return wrapper
    return func_wrapper


class GlutzController:
    """Structure Glutz functions for hass."""

    def __init__(self, hass, conf):
        """Init Hass Devices"""
        self._hass = hass
        self._conf = conf

        self._url = conf[CONF_URL]
        self._session = async_get_clientsession(hass)
        self._proxy = conf[CONF_PROXY]
        self._username = conf[CONF_USERNAME]
        self._password = conf[CONF_PASSWORD]
        self._stats = {'errors': 0, 'requests': 0}

    async def discover_access_points(self):
        return await self._request('eAccess.getModel', ["AccessPoints", {}, ["id", "label", "function", "status"]])

    async def fetch_access_point_status(self, access_point_id) -> int:
        result = await self._request('eAccess.getModel', ["AccessPoints", {'id': access_point_id}, ["id", "status"]])

        return result[0].get('state', 'locked')

    async def open_access_point(self, access_point_id):
        return await self._request('eAccess.openAccessPoint', [access_point_id])

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            connector = aiohttp.TCPConnector(force_close=True)
            self._session = aiohttp.ClientSession(connector=connector)

        return self._session

    @retry()
    async def _request(self, method_name, params):
        json = {
            'method': method_name,
            'params': params,
            'id': 'ha-glutz-' + str(self._stats['requests']),
            'jsonrpc': '2.0'
        }

        auth = None

        if self._username is not None:
            auth = aiohttp.helpers.BasicAuth(self._username, self._password)

        async with self._get_session().post(self._url, json=json, proxy=self._proxy,auth=auth) as r:
            result = await r.json()

            _LOGGER.debug('glutz_request: (%d) %s -- %s -- %s', r.status, str(json), str(result), str(r.request_info))
            # print("Result", r.status, str(result), str(r.request_info))
            r.raise_for_status()

            return result.get('result')

    # @property
    # def control4(self):
    #    return self._control4
