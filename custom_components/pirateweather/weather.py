"""Support for the Pirate Weather (PW) service."""
from __future__ import annotations

from datetime import timedelta
import logging

import forecastio
from requests.exceptions import ConnectionError as ConnectError, HTTPError, Timeout
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
from homeassistant.util.dt import utc_from_timestamp
from homeassistant.util.pressure import convert as convert_pressure
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

import forecastio

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
    DEFAULT_FORECAST_MODE,
    DEFAULT_LANGUAGE,
    DEFAULT_NAME,
    DOMAIN,
    FORECAST_MODES,
    LANGUAGES,
    CONF_UNITS,
    DEFAULT_UNITS,
    ENTRY_NAME,
    ENTRY_WEATHER_COORDINATOR,
    FORECAST_MODES,
    PLATFORMS,
    UPDATE_LISTENER,   
    MANUFACTURER,    
    FORECASTS_HOURLY,
    FORECASTS_DAILY,
)


_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by Pirate Weather GUI"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_MODE, default="hourly"): vol.In(FORECAST_MODES),
        vol.Optional(CONF_UNITS): vol.In(["auto", "si", "us", "ca", "uk", "uk2"]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

MAP_CONDITION = {
    "clear-day": ATTR_CONDITION_SUNNY,
    "clear-night": ATTR_CONDITION_CLEAR_NIGHT,
    "rain": ATTR_CONDITION_RAINY,
    "snow": ATTR_CONDITION_SNOWY,
    "sleet": ATTR_CONDITION_SNOWY_RAINY,
    "wind": ATTR_CONDITION_WINDY,
    "fog": ATTR_CONDITION_FOG,
    "cloudy": ATTR_CONDITION_CLOUDY,
    "partly-cloudy-day": ATTR_CONDITION_PARTLYCLOUDY,
    "partly-cloudy-night": ATTR_CONDITION_PARTLYCLOUDY,
    "hail": ATTR_CONDITION_HAIL,
    "thunderstorm": ATTR_CONDITION_LIGHTNING,
    "tornado": None,
}

CONF_UNITS = "units"

DEFAULT_NAME = "Pirate Weather"

from .weather_update_coordinator import WeatherUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OpenWeatherMap weather entity based on a config entry."""
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    name = domain_data[CONF_NAME]
    weather_coordinator = domain_data[ENTRY_WEATHER_COORDINATOR]
    api_key = domain_data[CONF_API_KEY]
    latitude = domain_data[CONF_LATITUDE]
    longitude = domain_data[CONF_LONGITUDE]
    units = domain_data[CONF_UNITS]
    forecast_mode = domain_data[CONF_MODE]
    
    unique_id = f"{config_entry.unique_id}"
    
    #dark_sky = DarkSkyData(api_key, latitude, longitude, units, hass)
    
    #_LOGGER.info(weather_coordinator.__dict__)
    _LOGGER.info("PW CONF_MODE")
    _LOGGER.info(domain_data[CONF_MODE])
    _LOGGER.info(domain_data)
    _LOGGER.info(CONF_MODE)
    pw_weather = PirateWeather(name, unique_id, forecast_mode, weather_coordinator)

    async_add_entities([pw_weather], False)
    #_LOGGER.info(pw_weather.__dict__)
    

class PirateWeather(WeatherEntity):
    """Implementation of an PirateWeather sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_should_poll = False
    _attr_temperature_unit = TEMP_CELSIUS

    def __init__(
        self,
        name: str,
        unique_id,
        forecast_mode: str,
        weather_coordinator: WeatherUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, unique_id)},
            manufacturer=MANUFACTURER,
            name=DEFAULT_NAME,
        )
        self._weather_coordinator = weather_coordinator
        self._name = name
        self._mode = forecast_mode
        self._unique_id = unique_id 
        self._ds_data = self._weather_coordinator.data
        self._ds_currently = self._weather_coordinator.data.currently()
        self._ds_hourly = self._weather_coordinator.data.hourly()
        self._ds_daily = self._weather_coordinator.data.daily()

        _LOGGER.info(self._mode)


    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return self._unique_id
        
    @property
    def available(self):
        """Return if weather data is available from PirateWeather."""
        return self._weather_coordinator.data is not None

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def temperature(self):
        """Return the temperature."""
        return self._weather_coordinator.data.currently().d.get("temperature")

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        if self._weather_coordinator.data.json.get("flags").get("units") is None:
            return None
        return TEMP_FAHRENHEIT if "us" in self._weather_coordinator.data.json.get("flags").get("units") else TEMP_CELSIUS
                
    @property
    def humidity(self):
        """Return the humidity."""
        return round(self._weather_coordinator.data.currently().d.get("humidity") * 100.0, 2)

    @property
    def wind_speed(self):
        """Return the wind speed."""
        return self._weather_coordinator.data.currently().d.get("windSpeed")

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        return self._weather_coordinator.data.currently().d.get("windBearing")

    @property
    def ozone(self):
        """Return the ozone level."""
        return self._weather_coordinator.data.currently().d.get("ozone")

    @property
    def pressure(self):
        """Return the pressure."""
        pressure = self._weather_coordinator.data.currently().d.get("pressure")
        if "us" in self._weather_coordinator.data.json.get("flags").get("units"):
            return round(convert_pressure(pressure, PRESSURE_HPA, PRESSURE_INHG), 2)
        return round(pressure, 2)

    @property
    def visibility(self):
        """Return the visibility."""
        return self._weather_coordinator.data.currently().d.get("visibility")

    @property
    def condition(self):
        """Return the weather condition."""
        #_LOGGER.info(self._weather_coordinator.data.json.get("flags"))
        #_LOGGER.info(self._weather_coordinator.data.json.get("flags").get("units"))
        #_LOGGER.info(self._weather_coordinator.data.currently().__dict__)
        return MAP_CONDITION.get(self._weather_coordinator.data.currently().d.get("icon"))

    @property
    def forecast(self):
        """Return the forecast array."""
        # Per conversation with Joshua Reyes of Dark Sky, to get the total
        # forecasted precipitation, you have to multiple the intensity by
        # the hours for the forecast interval
        def calc_precipitation(intensity, hours):
            amount = None
            if intensity is not None:
                amount = round((intensity * hours), 1)
            return amount if amount > 0 else None

        data = None

        if self._mode == "daily":
            data = [
                {
                    ATTR_FORECAST_TIME: utc_from_timestamp(
                        entry.d.get("time")
                    ).isoformat(),
                    ATTR_FORECAST_TEMP: entry.d.get("temperatureHigh"),
                    ATTR_FORECAST_TEMP_LOW: entry.d.get("temperatureLow"),
                    #ATTR_FORECAST_PRECIPITATION: calc_precipitation(
                    #    entry.d.get("precipIntensity"), 24
                    #),
                    ATTR_FORECAST_PRECIPITATION: calc_precipitation(
                        entry.d.get("precipAccumulation"), 1
                    ),                    
                    ATTR_FORECAST_WIND_SPEED: entry.d.get("windSpeed"),
                    ATTR_FORECAST_WIND_BEARING: entry.d.get("windBearing"),
                    ATTR_FORECAST_CONDITION: MAP_CONDITION.get(entry.d.get("icon")),
                }
                for entry in self._weather_coordinator.data.daily().data
            ]
        else:
            data = [
                {
                    ATTR_FORECAST_TIME: utc_from_timestamp(
                        entry.d.get("time")
                    ).isoformat(),
                    ATTR_FORECAST_TEMP: entry.d.get("temperature"),
                    ATTR_FORECAST_PRECIPITATION: calc_precipitation(
                        entry.d.get("precipIntensity"), 1
                    ),
                    ATTR_FORECAST_CONDITION: MAP_CONDITION.get(entry.d.get("icon")),
                }
                for entry in self._weather_coordinator.data.hourly().data
            ]

        return data
    
    async def async_update(self) -> None:
        """Get the latest data from OWM and updates the states."""
        _LOGGER.info("PW_Weather_C")
        await self._weather_coordinator.async_request_refresh()   
        _LOGGER.info("PW_Weather_D")
         
#    async def update(self):
#        """Get the latest data from Dark Sky."""
#        await self._dark_sky.update()
#
#        self._ds_data = self._dark_sky.data
#        currently = self._dark_sky.currently
#        self._ds_currently = currently.d if currently else {}
#        self._ds_hourly = self._dark_sky.hourly
#        self._ds_daily = self._dark_sky.daily
        
    async def async_added_to_hass(self) -> None:
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self._weather_coordinator.async_add_listener(self.async_write_ha_state)
        )

    
    

        
        