"""DataUpdateCoordinator for WeatherKit integration."""
from __future__ import annotations

from datetime import timedelta

from apple_weatherkit import DataSetType
from apple_weatherkit.client import WeatherKitApiClient, WeatherKitApiClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed



from .const import (
    DOMAIN,
    LOGGER,
)

REQUESTED_DATA_SETS = [
    DataSetType.CURRENT_WEATHER,
    DataSetType.DAILY_FORECAST,
    DataSetType.HOURLY_FORECAST,
]

import json
import aiohttp
import asyncio


from pirate_weather.api import PirateWeatherAsync
from pirate_weather.types.languages import Languages
from pirate_weather.types.units import Units
from pirate_weather.types.weather import Weather

class PirateWeatherKitDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: PirateWeatherAsync,
        session: aiohttp.ClientSession,
        pw_scan_Int: timedelta,
    ) -> None:
        """Initialize."""
        self.client = client
        self.session = session
        self.hass = hass
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=pw_scan_Int,
        )


    async def _async_update_data(self):
        """Update the current weather and forecasts."""

        LOGGER.warning('PW Coordinator A') 
        LOGGER.warning(self.client)
        LOGGER.warning(self.session)
        
        forecast = await self.client.get_forecast(
          self.config_entry.data[CONF_LATITUDE],
          self.config_entry.data[CONF_LONGITUDE],
          extend=True,  # default `False`
          lang='en',  # default `ENGLISH`
          values_units='si',  # default `auto`
          exclude=[],  # default `[]`,
          timezone='UTC',  # default None - will be set by Pirate Weather API automatically
           client_session=self.session  # default aiohttp.ClientSession()
          )

        
        LOGGER.warning('PW Coordinator B')  
        LOGGER.warning(forecast)
          
        return forecast

