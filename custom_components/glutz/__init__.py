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

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_URL = 'url'
CONF_PROXY = 'proxy'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_URL): cv.url,
        vol.Optional(CONF_PROXY, default=None): cv.url
    })
}, extra=vol.ALLOW_EXTRA)

DATA_GLUTZ = 'glutz'
DATA_GLUTZ_CONFIG = 'glutz_config'


async def async_setup(hass, config):
    """Setup Glutz eAccess Controller"""

    _LOGGER.debug('async_setup: %s', str(config))

    if DOMAIN not in config:
        return

    _LOGGER.debug('async_setup has config')

    # from control4 import Control4

    conf = config[DOMAIN]

    # May need to avoid aviod 'session=async_get_clientsession(hass)' here,
    # because Control4 seems to require force_close -- TBD
    # control4 = Control4(url=conf['url'], session=async_get_clientsession(hass), proxy=conf['proxy'])

    glutz = GlutzController(hass, conf)

    hass.data[DATA_GLUTZ_CONFIG] = conf
    hass.data[DATA_GLUTZ] = glutz

    await glutz.init()

    return True


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

        self._url = url
        self._session = session
        self._proxy = proxy
        self._stats = {'errors': 0, 'requests': 0}


    async def discover_access_points(self):
        return await self._request('eAccess.getModel', ["AccessPoints", {}, ["id", "label", "function", "status"]])


    async def fetch_access_point_status(self, access_point_id):
        result = await self._request('eAccess.getModel', ["AccessPoints", {}, ["id","status"]])

        return result.get('state', 'locked')


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
            method: method_name,
            params: params,
            id: 'ha-glutz-' + str(self._stats.requests),
            jsonrpc: '2.0'
        }

        async with self._get_session().post(self._url, json=json, proxy=self._proxy) as r:
            result = await
            r.text()

            _LOGGER.debug('glutz_request: (%d) %s -- %s', r.status, str(result), str(r.request_info))
            print("Result", r.status, str(result), str(r.request_info))
            r.raise_for_status()

            return result


    # @property
    # def control4(self):
    #    return self._control4
