"""Support for PirateWeather (Dark Sky Compatable weather service."""
from datetime import timedelta
import logging

import forecastio
from requests.exceptions import ConnectionError as ConnectError, HTTPError, Timeout
import voluptuous as vol

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from homeassistant.components.sensor import (
    DEVICE_CLASS_TEMPERATURE,
    PLATFORM_SCHEMA,
    SensorEntity,
)

from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    DEGREE,
    LENGTH_CENTIMETERS,
    LENGTH_KILOMETERS,
    PERCENTAGE,
    PRECIPITATION_MILLIMETERS_PER_HOUR,
    PRESSURE_MBAR,
    SPEED_KILOMETERS_PER_HOUR,
    SPEED_METERS_PER_SECOND,
    SPEED_MILES_PER_HOUR,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    UV_INDEX,
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

import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

from .weather_update_coordinator import WeatherUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by PirateWeather"

CONF_FORECAST = "forecast"
CONF_HOURLY_FORECAST = "hourly_forecast"
CONF_LANGUAGE = "language"
CONF_UNITS = "units"

DEFAULT_LANGUAGE = "en"
DEFAULT_NAME = "PirateWeather"
SCAN_INTERVAL = timedelta(seconds=900)

DEPRECATED_SENSOR_TYPES = {
    "apparent_temperature_max",
    "apparent_temperature_min",
    "temperature_max",
    "temperature_min",
}


# Sensor types are defined like so:
# Name, si unit, us unit, ca unit, uk unit, uk2 unit
SENSOR_TYPES = {
    "summary": [
        "Summary",
        None,
        None,
        None,
        None,
        None,
        None,
        ["currently", "hourly", "daily"],
    ],
    "minutely_summary": ["Minutely Summary", None, None, None, None, None, None, []],
    "hourly_summary": ["Hourly Summary", None, None, None, None, None, None, []],
    "daily_summary": ["Daily Summary", None, None, None, None, None, None, []],
    "icon": [
        "Icon",
        None,
        None,
        None,
        None,
        None,
        None,
        ["currently", "hourly", "daily"],
    ],
    "nearest_storm_distance": [
        "Nearest Storm Distance",
        LENGTH_KILOMETERS,
        "mi",
        LENGTH_KILOMETERS,
        LENGTH_KILOMETERS,
        "mi",
        "mdi:weather-lightning",
        ["currently"],
    ],
    "nearest_storm_bearing": [
        "Nearest Storm Bearing",
        DEGREE,
        DEGREE,
        DEGREE,
        DEGREE,
        DEGREE,
        "mdi:weather-lightning",
        ["currently"],
    ],
    "precip_type": [
        "Precip",
        None,
        None,
        None,
        None,
        None,
        "mdi:weather-pouring",
        ["currently", "minutely", "hourly", "daily"],
    ],
    "precip_intensity": [
        "Precip Intensity",
        PRECIPITATION_MILLIMETERS_PER_HOUR,
        "in",
        PRECIPITATION_MILLIMETERS_PER_HOUR,
        PRECIPITATION_MILLIMETERS_PER_HOUR,
        PRECIPITATION_MILLIMETERS_PER_HOUR,
        "mdi:weather-rainy",
        ["currently", "minutely", "hourly", "daily"],
    ],
    "precip_probability": [
        "Precip Probability",
        PERCENTAGE,
        PERCENTAGE,
        PERCENTAGE,
        PERCENTAGE,
        PERCENTAGE,
        "mdi:water-percent",
        ["currently", "minutely", "hourly", "daily"],
    ],
    "precip_accumulation": [
        "Precip Accumulation",
        LENGTH_CENTIMETERS,
        "in",
        LENGTH_CENTIMETERS,
        LENGTH_CENTIMETERS,
        LENGTH_CENTIMETERS,
        "mdi:weather-snowy",
        ["hourly", "daily"],
    ],
    "temperature": [
        "Temperature",
        TEMP_CELSIUS,
        TEMP_FAHRENHEIT,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        "mdi:thermometer",
        ["currently", "hourly"],
    ],
    "apparent_temperature": [
        "Apparent Temperature",
        TEMP_CELSIUS,
        TEMP_FAHRENHEIT,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        "mdi:thermometer",
        ["currently", "hourly"],
    ],
    "dew_point": [
        "Dew Point",
        TEMP_CELSIUS,
        TEMP_FAHRENHEIT,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        "mdi:thermometer",
        ["currently", "hourly", "daily"],
    ],
    "wind_speed": [
        "Wind Speed",
        SPEED_METERS_PER_SECOND,
        SPEED_MILES_PER_HOUR,
        SPEED_KILOMETERS_PER_HOUR,
        SPEED_MILES_PER_HOUR,
        SPEED_MILES_PER_HOUR,
        "mdi:weather-windy",
        ["currently", "hourly", "daily"],
    ],
    "wind_bearing": [
        "Wind Bearing",
        DEGREE,
        DEGREE,
        DEGREE,
        DEGREE,
        DEGREE,
        "mdi:compass",
        ["currently", "hourly", "daily"],
    ],
    "wind_gust": [
        "Wind Gust",
        SPEED_METERS_PER_SECOND,
        SPEED_MILES_PER_HOUR,
        SPEED_KILOMETERS_PER_HOUR,
        SPEED_MILES_PER_HOUR,
        SPEED_MILES_PER_HOUR,
        "mdi:weather-windy-variant",
        ["currently", "hourly", "daily"],
    ],
    "cloud_cover": [
        "Cloud Coverage",
        PERCENTAGE,
        PERCENTAGE,
        PERCENTAGE,
        PERCENTAGE,
        PERCENTAGE,
        "mdi:weather-partly-cloudy",
        ["currently", "hourly", "daily"],
    ],
    "humidity": [
        "Humidity",
        PERCENTAGE,
        PERCENTAGE,
        PERCENTAGE,
        PERCENTAGE,
        PERCENTAGE,
        "mdi:water-percent",
        ["currently", "hourly", "daily"],
    ],
    "pressure": [
        "Pressure",
        PRESSURE_MBAR,
        PRESSURE_MBAR,
        PRESSURE_MBAR,
        PRESSURE_MBAR,
        PRESSURE_MBAR,
        "mdi:gauge",
        ["currently", "hourly", "daily"],
    ],
    "visibility": [
        "Visibility",
        LENGTH_KILOMETERS,
        "mi",
        LENGTH_KILOMETERS,
        LENGTH_KILOMETERS,
        "mi",
        "mdi:eye",
        ["currently", "hourly", "daily"],
    ],
    "ozone": [
        "Ozone",
        "DU",
        "DU",
        "DU",
        "DU",
        "DU",
        "mdi:eye",
        ["currently", "hourly", "daily"],
    ],
    "apparent_temperature_max": [
        "Daily High Apparent Temperature",
        TEMP_CELSIUS,
        TEMP_FAHRENHEIT,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        "mdi:thermometer",
        ["daily"],
    ],
    "apparent_temperature_high": [
        "Daytime High Apparent Temperature",
        TEMP_CELSIUS,
        TEMP_FAHRENHEIT,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        "mdi:thermometer",
        ["daily"],
    ],
    "apparent_temperature_min": [
        "Daily Low Apparent Temperature",
        TEMP_CELSIUS,
        TEMP_FAHRENHEIT,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        "mdi:thermometer",
        ["daily"],
    ],
    "apparent_temperature_low": [
        "Overnight Low Apparent Temperature",
        TEMP_CELSIUS,
        TEMP_FAHRENHEIT,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        "mdi:thermometer",
        ["daily"],
    ],
    "temperature_max": [
        "Daily High Temperature",
        TEMP_CELSIUS,
        TEMP_FAHRENHEIT,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        "mdi:thermometer",
        ["daily"],
    ],
    "temperature_high": [
        "Daytime High Temperature",
        TEMP_CELSIUS,
        TEMP_FAHRENHEIT,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        "mdi:thermometer",
        ["daily"],
    ],
    "temperature_min": [
        "Daily Low Temperature",
        TEMP_CELSIUS,
        TEMP_FAHRENHEIT,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        "mdi:thermometer",
        ["daily"],
    ],
    "temperature_low": [
        "Overnight Low Temperature",
        TEMP_CELSIUS,
        TEMP_FAHRENHEIT,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        TEMP_CELSIUS,
        "mdi:thermometer",
        ["daily"],
    ],
    "precip_intensity_max": [
        "Daily Max Precip Intensity",
        PRECIPITATION_MILLIMETERS_PER_HOUR,
        "in",
        PRECIPITATION_MILLIMETERS_PER_HOUR,
        PRECIPITATION_MILLIMETERS_PER_HOUR,
        PRECIPITATION_MILLIMETERS_PER_HOUR,
        "mdi:thermometer",
        ["daily"],
    ],
    "uv_index": [
        "UV Index",
        UV_INDEX,
        UV_INDEX,
        UV_INDEX,
        UV_INDEX,
        UV_INDEX,
        "mdi:weather-sunny",
        ["currently", "hourly", "daily"],
    ],
    "moon_phase": [
        "Moon Phase",
        None,
        None,
        None,
        None,
        None,
        "mdi:weather-night",
        ["daily"],
    ],
    "sunrise_time": [
        "Sunrise",
        None,
        None,
        None,
        None,
        None,
        "mdi:white-balance-sunny",
        ["daily"],
    ],
    "sunset_time": [
        "Sunset",
        None,
        None,
        None,
        None,
        None,
        "mdi:weather-night",
        ["daily"],
    ],
    "alerts": ["Alerts", None, None, None, None, None, "mdi:alert-circle-outline", []],
}

CONDITION_PICTURES = {
    "clear-day": ["/static/images/darksky/weather-sunny.svg", "mdi:weather-sunny"],
    "clear-night": ["/static/images/darksky/weather-night.svg", "mdi:weather-night"],
    "rain": ["/static/images/darksky/weather-pouring.svg", "mdi:weather-pouring"],
    "snow": ["/static/images/darksky/weather-snowy.svg", "mdi:weather-snowy"],
    "sleet": ["/static/images/darksky/weather-hail.svg", "mdi:weather-snowy-rainy"],
    "wind": ["/static/images/darksky/weather-windy.svg", "mdi:weather-windy"],
    "fog": ["/static/images/darksky/weather-fog.svg", "mdi:weather-fog"],
    "cloudy": ["/static/images/darksky/weather-cloudy.svg", "mdi:weather-cloudy"],
    "partly-cloudy-day": [
        "/static/images/darksky/weather-partlycloudy.svg",
        "mdi:weather-partly-cloudy",
    ],
    "partly-cloudy-night": [
        "/static/images/darksky/weather-cloudy.svg",
        "mdi:weather-night-partly-cloudy",
    ],
}

# Language Supported Codes
LANGUAGE_CODES = [
    "ar",
    "az",
    "be",
    "bg",
    "bn",
    "bs",
    "ca",
    "cs",
    "da",
    "de",
    "el",
    "en",
    "ja",
    "ka",
    "kn",
    "ko",
    "eo",
    "es",
    "et",
    "fi",
    "fr",
    "he",
    "hi",
    "hr",
    "hu",
    "id",
    "is",
    "it",
    "kw",
    "lv",
    "ml",
    "mr",
    "nb",
    "nl",
    "pa",
    "pl",
    "pt",
    "ro",
    "ru",
    "sk",
    "sl",
    "sr",
    "sv",
    "ta",
    "te",
    "tet",
    "tr",
    "uk",
    "ur",
    "x-pig-latin",
    "zh",
    "zh-tw",
]

ALLOWED_UNITS = ["auto", "si", "us", "ca", "uk", "uk2"]

ALERTS_ATTRS = ["time", "description", "expires", "severity", "uri", "regions", "title"]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_MONITORED_CONDITIONS): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        ),
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UNITS): vol.In(ALLOWED_UNITS),
        vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(LANGUAGE_CODES),
        vol.Inclusive(
            CONF_LATITUDE, "coordinates", "Latitude and longitude must exist together"
        ): cv.latitude,
        vol.Inclusive(
            CONF_LONGITUDE, "coordinates", "Latitude and longitude must exist together"
        ): cv.longitude,
        vol.Optional(CONF_FORECAST): vol.All(cv.ensure_list, [vol.Range(min=0, max=7)]),
        vol.Optional(CONF_HOURLY_FORECAST): vol.All(
            cv.ensure_list, [vol.Range(min=0, max=48)]
        ),
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pirate Weather sensor entities based on a config entry."""
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    name = domain_data[CONF_NAME]
    weather_coordinator = domain_data[ENTRY_WEATHER_COORDINATOR]
    api_key = domain_data[CONF_API_KEY]
    latitude = domain_data[CONF_LATITUDE]
    longitude = domain_data[CONF_LONGITUDE]
    units = domain_data[CONF_UNITS]
    forecast_mode = domain_data[CONF_MODE]
    conditions = domain_data(CONF_MONITORED_CONDITIONS)
    
    forecast_days = domain_data[FORECASTS_DAILY]
    forecast_hours = domain_data[FORECASTS_HOURLY]
    unique_id = f"{config_entry.unique_id}"

    sensors: list[AccuWeatherSensor] = []
    for condition in conditions:
      if forecast_days is not None:
        for forecast_day in forecast_days:
          unique_id = f"{config_entry.unique_id}-{condition}-daily-{forecast_day}"
          forecast_hour = None
          
          sensors.append(AccuWeatherSensor(name, unique_id, coordinator, forecast_day, forecast_hour, condition))
      elif forecast_hours is not None:
        for forecast_hour in forecast_hours:
          unique_id = f"{config_entry.unique_id}-{condition}-hourly-{forecast_hour}"
          forecast_day = None
          sensors.append(AccuWeatherSensor(name, unique_id, coordinator, forecast_day, forecast_hour, condition))

    async_add_entities(sensors)
    
    
    forecast = config.get(CONF_FORECAST)
    forecast_hour = config.get(CONF_HOURLY_FORECAST)
    sensors = []
    

    for variable in config[CONF_MONITORED_CONDITIONS]:
    
    
        """Return the name of the sensor."""
        if self.forecast_day is not None:
            return f"{self.client_name} {self._name} {self.forecast_day}d"
        if self.forecast_hour is not None:
            return f"{self.client_name} {self._name} {self.forecast_hour}h"
        return f"{self.client_name} {self._name}"
        
        
        
        if variable in DEPRECATED_SENSOR_TYPES:
            _LOGGER.warning("Monitored condition %s is deprecated", variable)
        if not SENSOR_TYPES[variable][7] or "currently" in SENSOR_TYPES[variable][7]:
            if variable == "alerts":
                sensors.append(DarkSkyAlertSensor(forecast_data, variable, name))
            else:
                sensors.append(DarkSkySensor(forecast_data, variable, name))

        if forecast is not None and "daily" in SENSOR_TYPES[variable][7]:
            for forecast_day in forecast:
                sensors.append(
                    DarkSkySensor(
                        forecast_data, variable, name, forecast_day=forecast_day
                    )
                )
        if forecast_hour is not None and "hourly" in SENSOR_TYPES[variable][7]:
            for forecast_h in forecast_hour:
                sensors.append(
                    DarkSkySensor(
                        forecast_data, variable, name, forecast_hour=forecast_h
                    )
                )

    add_entities(sensors, True)



class PirateWeatherSensor(SensorEntity):
    """Class for an PirateWeather sensor."""

    _attr_should_poll = False
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        name: str,
        unique_id,
        weather_coordinator: WeatherUpdateCoordinator,
        forecast_day: int,
        forecast_hour: int,
        condition: str,
    ) -> None:
        """Initialize the sensor."""
        self._weather_coordinator = weather_coordinator
        
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, unique_id)},
            manufacturer=MANUFACTURER,
            name=DEFAULT_NAME,
        )

        self._ds_data = self._weather_coordinator.data
        self._ds_currently = self._weather_coordinator.data.currently()
        self._ds_hourly = self._weather_coordinator.data.hourly()
        self._ds_daily = self._weather_coordinator.data.daily()
        
        self.forecast_day = forecast_day
        self.forecast_hour = forecast_hour
        self.type = condition
        self._state = None
        self._icon = None
        self._unit_of_measurement = None
        

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._coordinator.last_update_success


    @property
    def native_value(self) -> StateType:
        """Return the state of the device."""
        return self._weather_coordinator.data.get(self.entity_description.key, None)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def unit_system(self):
        """Return the unit system of this entity."""
        return self._weather_coordinator.data.json.get("flags").get("units")

    @property
    def entity_picture(self):
        """Return the entity picture to use in the frontend, if any."""
        if self._icon is None or "summary" not in self.type:
            return None

        if self._icon in CONDITION_PICTURES:
            return CONDITION_PICTURES[self._icon][0]

        return None

    def update_unit_of_measurement(self):
        """Update units based on unit system."""
        unit_index = {"si": 1, "us": 2, "ca": 3, "uk": 4, "uk2": 5}.get(
            self.unit_system, 1
        )
        self._unit_of_measurement = SENSOR_TYPES[self.type][unit_index]

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if "summary" in self.type and self._icon in CONDITION_PICTURES:
            return CONDITION_PICTURES[self._icon][1]

        return SENSOR_TYPES[self.type][6]

    @property
    def device_class(self):
        """Device class of the entity."""
        if SENSOR_TYPES[self.type][1] == TEMP_CELSIUS:
            return DEVICE_CLASS_TEMPERATURE

        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {ATTR_ATTRIBUTION: ATTRIBUTION}

    def get_state(self, data):
        """
        Return a new state based on the type.

        If the sensor type is unknown, the current state is returned.
        """
        lookup_type = convert_to_camel(self.type)
        state = getattr(data, lookup_type, None)

        if state is None:
            return state

        if "summary" in self.type:
            self._icon = getattr(data, "icon", "")

        # Some state data needs to be rounded to whole values or converted to
        # percentages
        if self.type in ["precip_probability", "cloud_cover", "humidity"]:
            return round(state * 100, 1)

        if self.type in [
            "dew_point",
            "temperature",
            "apparent_temperature",
            "temperature_low",
            "apparent_temperature_low",
            "temperature_min",
            "apparent_temperature_min",
            "temperature_high",
            "apparent_temperature_high",
            "temperature_max",
            "apparent_temperature_max",
            "precip_accumulation",
            "pressure",
            "ozone",
            "uvIndex",
        ]:
            return round(state, 1)
        return state

    async def async_added_to_hass(self) -> None:
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )
    async def async_update(self) -> None:
        """Get the latest data from PW and updates the states."""
        _LOGGER.info("PW_Sensor_C")
        await self._coordinator.async_request_refresh()   
        _LOGGER.info("PW_Sensor_D")
        
        if self.type == "minutely_summary":
            minutely = self._weather_coordinator.data.minutely()
            self._state = getattr(minutely, "summary", "")
            self._icon = getattr(minutely, "icon", "")
        elif self.type == "hourly_summary":
            hourly = self._weather_coordinator.data.hourly()
            self._state = getattr(hourly, "summary", "")
            self._icon = getattr(hourly, "icon", "")
        elif self.forecast_hour is not None:
            hourly = self._weather_coordinator.data.hourly()
            if hasattr(hourly, "data"):
                self._state = self.get_state(hourly.data[self.forecast_hour])
            else:
                self._state = 0
        elif self.type == "daily_summary":
            daily = self._weather_coordinator.data.daily()
            self._state = getattr(daily, "summary", "")
            self._icon = getattr(daily, "icon", "")
        elif self.forecast_day is not None:
            daily = self._weather_coordinator.data.daily()
            if hasattr(daily, "data"):
                self._state = self.get_state(daily.data[self.forecast_day])
            else:
                self._state = 0
        else:
            self.forecast_data.update_currently()
            currently = self.forecast_data.data_currently
            self._state = self.get_state(currently)


def convert_to_camel(data):
    """
    Convert snake case (foo_bar_bat) to camel case (fooBarBat).

    This is not pythonic, but needed for certain situations.
    """
    components = data.split("_")
    capital_components = "".join(x.title() for x in components[1:])
    return f"{components[0]}{capital_components}"


