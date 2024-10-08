"""Weather data coordinator for the Pirate Weather service."""

import json
import logging
from http.client import HTTPException

import aiohttp
import async_timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
)
from .forecast_models import Forecast

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by Pirate Weather"


class WeatherUpdateCoordinator(DataUpdateCoordinator):
    """Weather data update coordinator."""

    def __init__(self, api_key, latitude, longitude, pw_scan_Int, hass):
        """Initialize coordinator."""
        self._api_key = api_key
        self.latitude = latitude
        self.longitude = longitude
        self.pw_scan_Int = pw_scan_Int
        self.requested_units = "si"

        self.data = None
        self.currently = None
        self.hourly = None
        self.daily = None
        self._connect_error = False

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=pw_scan_Int)

    async def _async_update_data(self):
        """Update the data."""
        data = {}
        async with async_timeout.timeout(60):
            try:
                data = await self._get_pw_weather()
            except HTTPException as err:
                raise UpdateFailed(f"Error communicating with API: {err}") from err
        return data

    async def _get_pw_weather(self):
        """Poll weather data from PW."""

        if self.latitude == 0.0:
            requestLatitude = self.hass.config.latitude
        else:
            requestLatitude = self.latitude

        if self.longitude == 0.0:
            requestLongitude = self.hass.config.latitude
        else:
            requestLongitude = self.longitude

        forecastString = (
            "https://api.pirateweather.net/forecast/"
            + self._api_key
            + "/"
            + str(requestLatitude)
            + ","
            + str(requestLongitude)
            + "?units="
            + self.requested_units
            + "&extend=hourly"
            + "&version=2"
        )

        async with (
            aiohttp.ClientSession(raise_for_status=True) as session,
            session.get(forecastString) as resp,
        ):
            resptext = await resp.text()
            jsonText = json.loads(resptext)
            headers = resp.headers
            status = resp.raise_for_status()

            _LOGGER.debug("Pirate Weather data update")

            return Forecast(jsonText, status, headers)
