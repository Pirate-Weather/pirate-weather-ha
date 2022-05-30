"""Weather data coordinator for the OpenWeatherMap (OWM) service."""
from datetime import timedelta
import logging

import async_timeout
from pyowm.commons.exceptions import APIRequestError, UnauthorizedError
import forecastio
from forecastio.models import Forecast
import json
import aiohttp
import asyncio

from requests.exceptions import ConnectionError as ConnectError, HTTPError, Timeout
import voluptuous as vol

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_SUNNY,
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_PRESSURE,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
)
from homeassistant.helpers import sun
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt
from homeassistant.util.temperature import kelvin_to_celsius

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    PLATFORM_SCHEMA,
    WeatherEntity,
)
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODE,
    CONF_NAME,
    PRESSURE_HPA,
    PRESSURE_INHG,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)


from .const import (
    CONF_LANGUAGE,
    CONFIG_FLOW_VERSION,
    DOMAIN,
    ENTRY_NAME,
    ENTRY_WEATHER_COORDINATOR,
    PLATFORMS,
    UPDATE_LISTENER,
    CONF_UNITS,
    DEFAULT_UNITS,
)
_LOGGER = logging.getLogger(__name__)

WEATHER_UPDATE_INTERVAL = timedelta(minutes=15)
ATTRIBUTION = "Powered by Pirate Weather"

        
#class DarkSkyData:
#    """Get the latest data from PirateWeather."""
#
#    def __init__(self, api_key, latitude, longitude, units, hass):
#        """Initialize the data object."""
#        self._api_key = api_key
#        self.latitude = latitude
#        self.longitude = longitude
#        self.requested_units = units
#
#        self.data = None
#        self.currently = None
#        self.hourly = None
#        self.daily = None
#        self._connect_error = False
#
#    def update(self):
#        """Get the latest data from PirateWeather."""
#        try:
#            #self.data = forecastio.load_forecast(
#            #    self._api_key, self.latitude, self.longitude, units=self.requested_units
#            #)
#            forecastString = "https://api.pirateweather.net/forecast/" +  self._api_key + "/" + str(self.latitude) + "," + str(self.longitude) + "?units=" + self.requested_units
#            self.data = forecastio.manual(forecastString)
#
#            if self._connect_error:
#                self._connect_error = False
#                _LOGGER.info("Reconnected to PirateWeather")
#        except (ConnectError, HTTPError, Timeout, ValueError) as error:
#            if not self._connect_error:
#                self._connect_error = True
#                _LOGGER.error("Unable to connect to PirateWeather. %s", error)
#            self.data = None
#            
#        return data

#    @property
#    def units(self):
#        """Get the unit system of returned data."""
#        if self.data is None:
#            return None
#        return self.data.json.get("flags").get("units")
        
        
class WeatherUpdateCoordinator(DataUpdateCoordinator):
    """Weather data update coordinator."""

    def __init__(self, api_key, latitude, longitude, units, forecast_mode, hass):
        """Initialize coordinator."""
        self._api_key = api_key
        self.latitude = latitude
        self.longitude = longitude
        self.requested_units = units
        
        self.data = None
        self.currently = None
        self.hourly = None
        self.daily = None
        self._connect_error = False

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=WEATHER_UPDATE_INTERVAL
        )
        _LOGGER.info(WEATHER_UPDATE_INTERVAL)          
                 
                        
    async def _async_update_data(self):
        """Update the data."""
        data = {}
        #_LOGGER.info("PW_Update_Data_A")
        async with async_timeout.timeout(20):
            try:
                data = await self._get_pw_weather()
                #_LOGGER.info("PW_Update_Data_B")
            except (APIRequestError, UnauthorizedError) as error:
                raise UpdateFailed(error) from error
        return data

    async def _get_pw_weather(self):
        """Poll weather data from OWM."""
        _LOGGER.info("Made it to get PW V10")        
        forecastString = "https://api.pirateweather.net/forecast/" +  self._api_key + "/" + str(self.latitude) + "," + str(self.longitude) + "?units=" + self.requested_units
        #data = await self.hass.async_add_executor_job(forecastio.manual(forecastString))
        
        async with aiohttp.ClientSession(raise_for_status=True) as session:
          async with session.get(forecastString) as resp:
            #_LOGGER.info(resp.status)
            _LOGGER.info("PW_Update_Data_C")
            resptext = await resp.text()
            jsonText = json.loads(resptext)
            headers = resp.headers
            status = resp.raise_for_status()
            
            data = Forecast(jsonText, status, headers)
            #_LOGGER.info(data)
                
        return data

