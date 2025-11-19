"""Weather data coordinator for the Pirate Weather service."""

import logging

import async_timeout
from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
)
from .forecast_models import Forecast

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by Pirate Weather"


class WeatherUpdateCoordinator(DataUpdateCoordinator):
    """Weather data update coordinator."""

    def __init__(
        self,
        api_key,
        latitude,
        longitude,
        scan_interval,
        language,
        endpoint,
        units,
        hass,
        config_entry: ConfigEntry,
        models: str | None,
    ):
        """Initialize coordinator."""
        self._api_key = api_key
        self.latitude = latitude
        self.longitude = longitude
        self.scan_interval = scan_interval
        self.language = language
        self.endpoint = endpoint
        self.requested_units = units or "si"
        self.models = models

        self.data = None
        self.currently = None
        self.hourly = None
        self.daily = None
        self._connect_error = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
            config_entry=config_entry,
        )

    async def _async_update_data(self):
        """Update the data."""
        data = {}
        async with async_timeout.timeout(60):
            try:
                data = await self._get_pw_weather()
            except ClientError as err:
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
            self.endpoint
            + "/forecast/"
            + self._api_key
            + "/"
            + str(requestLatitude)
            + ","
            + str(requestLongitude)
            + "?units="
            + self.requested_units
            + "&extend=hourly"
            + "&version=2"
            + "&lang="
            + self.language
            + "&include=day_night_forecast"
        )
        if self.models:
            exclusions = ",".join(
                m.strip() for m in self.models.split(",") if m.strip()
            )
            if exclusions:
                forecastString += "&exclude=" + exclusions

        session = async_get_clientsession(self.hass)
        async with session.get(forecastString) as resp:
            resp.raise_for_status()
            jsonText = await resp.json()
            headers = resp.headers
            _LOGGER.debug("Pirate Weather data update from: %s", self.endpoint)
            return Forecast(jsonText, resp, headers)
