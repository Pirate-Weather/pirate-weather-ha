"""Weather data coordinator for the OpenWeatherMap (OWM) service."""
from datetime import timedelta
import logging

import async_timeout
import forecastio
from forecastio.models import Forecast
import json
import aiohttp
import asyncio

from requests.exceptions import ConnectionError as ConnectError, HTTPError, Timeout
import voluptuous as vol

from homeassistant.helpers import sun
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt


from .const import (
    DOMAIN,
)

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

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=pw_scan_Int
        )
               
                 
                        
    async def _async_update_data(self):
        """Update the data."""
        data = {}
        async with async_timeout.timeout(30):
            try:
                data = await self._get_pw_weather()
            except Exception as error:
                raise UpdateFailed(error) from error
        return data


    async def _get_pw_weather(self):
        """Poll weather data from PW."""   
        
             
        forecastString = "https://api.pirateweather.net/forecast/" +  self._api_key + "/" + str(self.latitude) + "," + str(self.longitude) + "?units=" + self.requested_units
        
        async with aiohttp.ClientSession(raise_for_status=True) as session:
          async with session.get(forecastString) as resp:
            resptext = await resp.text()
            jsonText = json.loads(resptext)
            headers = resp.headers
            status = resp.raise_for_status()
            
            data = Forecast(jsonText, status, headers)
                
        return data

