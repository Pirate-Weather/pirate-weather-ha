"""Support for PirateWeather (Dark Sky Compatable weather service."""
from datetime import timedelta
import logging

from dataclasses import dataclass, field

import forecastio
from requests.exceptions import ConnectionError as ConnectError, HTTPError, Timeout
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.template as template_helper


from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass
)
from typing import Literal, NamedTuple

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM

from homeassistant.components.sensor import (
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
    LENGTH_INCHES,
    LENGTH_KILOMETERS,
    LENGTH_MILES,
    LENGTH_MILLIMETERS,
    PERCENTAGE,
    PRECIPITATION_INCHES,
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
    DEFAULT_SCAN_INTERVAL,
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
    ALL_CONDITIONS,
    PW_PLATFORMS,
    PW_PLATFORM,
    PW_PREVPLATFORM,
    PW_ROUND,
)

from homeassistant.util import Throttle

from .weather_update_coordinator import WeatherUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by Pirate Weather"

CONF_FORECAST = "forecast"
CONF_HOURLY_FORECAST = "hourly_forecast"
CONF_LANGUAGE = "language"
CONF_UNITS = "units"

DEFAULT_LANGUAGE = "en"
DEFAULT_NAME = "PirateWeather"

DEPRECATED_SENSOR_TYPES = {
    "apparent_temperature_max",
    "apparent_temperature_min",
    "temperature_max",
    "temperature_min",
}

MAP_UNIT_SYSTEM: dict[
    Literal["si", "us", "ca", "uk", "uk2"],
    Literal["si_unit", "us_unit", "ca_unit", "uk_unit", "uk2_unit"],
] = {
    "si": "si_unit",
    "us": "us_unit",
    "ca": "ca_unit",
    "uk": "uk_unit",
    "uk2": "uk2_unit",
}

@dataclass
class PirateWeatherSensorEntityDescription(SensorEntityDescription):
    """Describes Pirate Weather sensor entity."""

    si_unit: str | None = None
    us_unit: str | None = None
    ca_unit: str | None = None
    uk_unit: str | None = None
    uk2_unit: str | None = None
    forecast_mode: list[str] = field(default_factory=list)
    
    
# Sensor Types    
SENSOR_TYPES: dict[str, PirateWeatherSensorEntityDescription] = {
    "summary": PirateWeatherSensorEntityDescription(
        key="summary",
        name="Summary",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "minutely_summary": PirateWeatherSensorEntityDescription(
        key="minutely_summary",
        name="Minutely Summary",
        forecast_mode=[],
    ),
    "hourly_summary": PirateWeatherSensorEntityDescription(
        key="hourly_summary",
        name="Hourly Summary",
        forecast_mode=[],
    ),
    "daily_summary": PirateWeatherSensorEntityDescription(
        key="daily_summary",
        name="Daily Summary",
        forecast_mode=[],
    ),
    "icon": PirateWeatherSensorEntityDescription(
        key="icon",
        name="Icon",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "nearest_storm_distance": PirateWeatherSensorEntityDescription(
        key="nearest_storm_distance",
        name="Nearest Storm Distance",
        si_unit=LENGTH_KILOMETERS,
        us_unit=LENGTH_MILES,
        ca_unit=LENGTH_KILOMETERS,
        uk_unit=LENGTH_KILOMETERS,
        uk2_unit=LENGTH_MILES,
        icon="mdi:weather-lightning",
        forecast_mode=["currently"],
    ),
    "nearest_storm_bearing": PirateWeatherSensorEntityDescription(
        key="nearest_storm_bearing",
        name="Nearest Storm Bearing",
        si_unit=DEGREE,
        us_unit=DEGREE,
        ca_unit=DEGREE,
        uk_unit=DEGREE,
        uk2_unit=DEGREE,
        icon="mdi:weather-lightning",
        forecast_mode=["currently"],
    ),
    "precip_type": PirateWeatherSensorEntityDescription(
        key="precip_type",
        name="Precip",
        icon="mdi:weather-pouring",
        forecast_mode=["currently", "minutely", "hourly", "daily"],
    ),
    "precip_intensity": PirateWeatherSensorEntityDescription(
        key="precip_intensity",
        name="Precip Intensity",
        si_unit=PRECIPITATION_MILLIMETERS_PER_HOUR,
        us_unit=PRECIPITATION_INCHES,
        ca_unit=PRECIPITATION_MILLIMETERS_PER_HOUR,
        uk_unit=PRECIPITATION_MILLIMETERS_PER_HOUR,
        uk2_unit=PRECIPITATION_MILLIMETERS_PER_HOUR,
        icon="mdi:weather-rainy",
        forecast_mode=["currently", "minutely", "hourly", "daily"],
    ),
    "precip_probability": PirateWeatherSensorEntityDescription(
        key="precip_probability",
        name="Precip Probability",
        si_unit=PERCENTAGE,
        us_unit=PERCENTAGE,
        ca_unit=PERCENTAGE,
        uk_unit=PERCENTAGE,
        uk2_unit=PERCENTAGE,
        icon="mdi:water-percent",
        forecast_mode=["currently", "minutely", "hourly", "daily"],
    ),
    "precip_accumulation": PirateWeatherSensorEntityDescription(
        key="precip_accumulation",
        name="Precip Accumulation",
        device_class=SensorDeviceClass.PRECIPITATION,
        si_unit=LENGTH_CENTIMETERS,
        us_unit=LENGTH_INCHES,
        ca_unit=LENGTH_CENTIMETERS,
        uk_unit=LENGTH_CENTIMETERS,
        uk2_unit=LENGTH_CENTIMETERS,
        icon="mdi:weather-snowy",
        forecast_mode=["hourly", "daily"],
    ),
    "temperature": PirateWeatherSensorEntityDescription(
        key="temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=TEMP_CELSIUS,
        us_unit=TEMP_FAHRENHEIT,
        ca_unit=TEMP_CELSIUS,
        uk_unit=TEMP_CELSIUS,
        uk2_unit=TEMP_CELSIUS,
        forecast_mode=["currently", "hourly"],
    ),
    "apparent_temperature": PirateWeatherSensorEntityDescription(
        key="apparent_temperature",
        name="Apparent Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=TEMP_CELSIUS,
        us_unit=TEMP_FAHRENHEIT,
        ca_unit=TEMP_CELSIUS,
        uk_unit=TEMP_CELSIUS,
        uk2_unit=TEMP_CELSIUS,
        forecast_mode=["currently", "hourly"],
    ),
    "dew_point": PirateWeatherSensorEntityDescription(
        key="dew_point",
        name="Dew Point",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=TEMP_CELSIUS,
        us_unit=TEMP_FAHRENHEIT,
        ca_unit=TEMP_CELSIUS,
        uk_unit=TEMP_CELSIUS,
        uk2_unit=TEMP_CELSIUS,
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "wind_speed": PirateWeatherSensorEntityDescription(
        key="wind_speed",
        name="Wind Speed",
        si_unit=SPEED_METERS_PER_SECOND,
        us_unit=SPEED_MILES_PER_HOUR,
        ca_unit=SPEED_KILOMETERS_PER_HOUR,
        uk_unit=SPEED_MILES_PER_HOUR,
        uk2_unit=SPEED_MILES_PER_HOUR,
        icon="mdi:weather-windy",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "wind_bearing": PirateWeatherSensorEntityDescription(
        key="wind_bearing",
        name="Wind Bearing",
        si_unit=DEGREE,
        us_unit=DEGREE,
        ca_unit=DEGREE,
        uk_unit=DEGREE,
        uk2_unit=DEGREE,
        icon="mdi:compass",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "wind_gust": PirateWeatherSensorEntityDescription(
        key="wind_gust",
        name="Wind Gust",
        device_class=SensorDeviceClass.WIND_SPEED,
        si_unit=SPEED_METERS_PER_SECOND,
        us_unit=SPEED_MILES_PER_HOUR,
        ca_unit=SPEED_KILOMETERS_PER_HOUR,
        uk_unit=SPEED_MILES_PER_HOUR,
        uk2_unit=SPEED_MILES_PER_HOUR,
        icon="mdi:weather-windy-variant",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "cloud_cover": PirateWeatherSensorEntityDescription(
        key="cloud_cover",
        name="Cloud Coverage",
        si_unit=PERCENTAGE,
        us_unit=PERCENTAGE,
        ca_unit=PERCENTAGE,
        uk_unit=PERCENTAGE,
        uk2_unit=PERCENTAGE,
        icon="mdi:weather-partly-cloudy",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "humidity": PirateWeatherSensorEntityDescription(
        key="humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=PERCENTAGE,
        us_unit=PERCENTAGE,
        ca_unit=PERCENTAGE,
        uk_unit=PERCENTAGE,
        uk2_unit=PERCENTAGE,
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "pressure": PirateWeatherSensorEntityDescription(
        key="pressure",
        name="Pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=PRESSURE_MBAR,
        us_unit=PRESSURE_MBAR,
        ca_unit=PRESSURE_MBAR,
        uk_unit=PRESSURE_MBAR,
        uk2_unit=PRESSURE_MBAR,
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "visibility": PirateWeatherSensorEntityDescription(
        key="visibility",
        name="Visibility",
        si_unit=LENGTH_KILOMETERS,
        us_unit=LENGTH_MILES,
        ca_unit=LENGTH_KILOMETERS,
        uk_unit=LENGTH_KILOMETERS,
        uk2_unit=LENGTH_MILES,
        icon="mdi:eye",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "ozone": PirateWeatherSensorEntityDescription(
        key="ozone",
        name="Ozone",
        device_class=SensorDeviceClass.OZONE,
        si_unit="DU",
        us_unit="DU",
        ca_unit="DU",
        uk_unit="DU",
        uk2_unit="DU",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "apparent_temperature_max": PirateWeatherSensorEntityDescription(
        key="apparent_temperature_max",
        name="Daily High Apparent Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        si_unit=TEMP_CELSIUS,
        us_unit=TEMP_FAHRENHEIT,
        ca_unit=TEMP_CELSIUS,
        uk_unit=TEMP_CELSIUS,
        uk2_unit=TEMP_CELSIUS,
        forecast_mode=["daily"],
    ),
    "apparent_temperature_high": PirateWeatherSensorEntityDescription(
        key="apparent_temperature_high",
        name="Daytime High Apparent Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        si_unit=TEMP_CELSIUS,
        us_unit=TEMP_FAHRENHEIT,
        ca_unit=TEMP_CELSIUS,
        uk_unit=TEMP_CELSIUS,
        uk2_unit=TEMP_CELSIUS,
        forecast_mode=["daily"],
    ),
    "apparent_temperature_min": PirateWeatherSensorEntityDescription(
        key="apparent_temperature_min",
        name="Daily Low Apparent Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        si_unit=TEMP_CELSIUS,
        us_unit=TEMP_FAHRENHEIT,
        ca_unit=TEMP_CELSIUS,
        uk_unit=TEMP_CELSIUS,
        uk2_unit=TEMP_CELSIUS,
        forecast_mode=["daily"],
    ),
    "apparent_temperature_low": PirateWeatherSensorEntityDescription(
        key="apparent_temperature_low",
        name="Overnight Low Apparent Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        si_unit=TEMP_CELSIUS,
        us_unit=TEMP_FAHRENHEIT,
        ca_unit=TEMP_CELSIUS,
        uk_unit=TEMP_CELSIUS,
        uk2_unit=TEMP_CELSIUS,
        forecast_mode=["daily"],
    ),
    "temperature_max": PirateWeatherSensorEntityDescription(
        key="temperature_max",
        name="Daily High Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        si_unit=TEMP_CELSIUS,
        us_unit=TEMP_FAHRENHEIT,
        ca_unit=TEMP_CELSIUS,
        uk_unit=TEMP_CELSIUS,
        uk2_unit=TEMP_CELSIUS,
        forecast_mode=["daily"],
    ),
    "temperature_high": PirateWeatherSensorEntityDescription(
        key="temperature_high",
        name="Daytime High Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        si_unit=TEMP_CELSIUS,
        us_unit=TEMP_FAHRENHEIT,
        ca_unit=TEMP_CELSIUS,
        uk_unit=TEMP_CELSIUS,
        uk2_unit=TEMP_CELSIUS,
        forecast_mode=["daily"],
    ),
    "temperature_min": PirateWeatherSensorEntityDescription(
        key="temperature_min",
        name="Daily Low Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        si_unit=TEMP_CELSIUS,
        us_unit=TEMP_FAHRENHEIT,
        ca_unit=TEMP_CELSIUS,
        uk_unit=TEMP_CELSIUS,
        uk2_unit=TEMP_CELSIUS,
        forecast_mode=["daily"],
    ),
    "temperature_low": PirateWeatherSensorEntityDescription(
        key="temperature_low",
        name="Overnight Low Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        si_unit=TEMP_CELSIUS,
        us_unit=TEMP_FAHRENHEIT,
        ca_unit=TEMP_CELSIUS,
        uk_unit=TEMP_CELSIUS,
        uk2_unit=TEMP_CELSIUS,
        forecast_mode=["daily"],
    ),
    "precip_intensity_max": PirateWeatherSensorEntityDescription(
        key="precip_intensity_max",
        name="Daily Max Precip Intensity",
        si_unit=PRECIPITATION_MILLIMETERS_PER_HOUR,
        us_unit=PRECIPITATION_INCHES,
        ca_unit=PRECIPITATION_MILLIMETERS_PER_HOUR,
        uk_unit=PRECIPITATION_MILLIMETERS_PER_HOUR,
        uk2_unit=PRECIPITATION_MILLIMETERS_PER_HOUR,
        icon="mdi:thermometer",
        forecast_mode=["daily"],
    ),
    "uv_index": PirateWeatherSensorEntityDescription(
        key="uv_index",
        name="UV Index",
        si_unit=UV_INDEX,
        us_unit=UV_INDEX,
        ca_unit=UV_INDEX,
        uk_unit=UV_INDEX,
        uk2_unit=UV_INDEX,
        icon="mdi:weather-sunny",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "moon_phase": PirateWeatherSensorEntityDescription(
        key="moon_phase",
        name="Moon Phase",
        icon="mdi:weather-night",
        forecast_mode=["daily"],
    ),
    "sunrise_time": PirateWeatherSensorEntityDescription(
        key="sunrise_time",
        name="Sunrise",
        icon="mdi:white-balance-sunny",
        forecast_mode=["daily"],
    ),
    "sunset_time": PirateWeatherSensorEntityDescription(
        key="sunset_time",
        name="Sunset",
        icon="mdi:weather-night",
        forecast_mode=["daily"],
    ),
    "alerts": PirateWeatherSensorEntityDescription(
        key="alerts",
        name="Alerts",
        icon="mdi:alert-circle-outline",
        forecast_mode=[],
    ),
}

class ConditionPicture(NamedTuple):
    """Entity picture and icon for condition."""

    entity_picture: str
    icon: str

CONDITION_PICTURES: dict[str, ConditionPicture] = {
    "clear-day": ConditionPicture(
        entity_picture="/static/images/darksky/weather-sunny.svg",
        icon="mdi:weather-sunny",
    ),
    "clear-night": ConditionPicture(
        entity_picture="/static/images/darksky/weather-night.svg",
        icon="mdi:weather-night",
    ),
    "rain": ConditionPicture(
        entity_picture="/static/images/darksky/weather-pouring.svg",
        icon="mdi:weather-pouring",
    ),
    "snow": ConditionPicture(
        entity_picture="/static/images/darksky/weather-snowy.svg",
        icon="mdi:weather-snowy",
    ),
    "sleet": ConditionPicture(
        entity_picture="/static/images/darksky/weather-hail.svg",
        icon="mdi:weather-snowy-rainy",
    ),
    "wind": ConditionPicture(
        entity_picture="/static/images/darksky/weather-windy.svg",
        icon="mdi:weather-windy",
    ),
    "fog": ConditionPicture(
        entity_picture="/static/images/darksky/weather-fog.svg",
        icon="mdi:weather-fog",
    ),
    "cloudy": ConditionPicture(
        entity_picture="/static/images/darksky/weather-cloudy.svg",
        icon="mdi:weather-cloudy",
    ),
    "partly-cloudy-day": ConditionPicture(
        entity_picture="/static/images/darksky/weather-partlycloudy.svg",
        icon="mdi:weather-partly-cloudy",
    ),
    "partly-cloudy-night": ConditionPicture(
        entity_picture="/static/images/darksky/weather-cloudy.svg",
        icon="mdi:weather-night-partly-cloudy",
    ),
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
   
HOURS = [i for i in range(49)]
DAYS = [i for i in range(7)]     
 
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UNITS): vol.In(ALLOWED_UNITS),
        vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(LANGUAGE_CODES),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,           
        vol.Inclusive(
            CONF_LATITUDE, "coordinates", "Latitude and longitude must exist together"
        ): cv.latitude,
        vol.Inclusive(
            CONF_LONGITUDE, "coordinates", "Latitude and longitude must exist together"
        ): cv.longitude,
        vol.Optional(PW_PLATFORM): cv.multi_select(
                  PW_PLATFORMS
              ),
        vol.Optional(PW_PREVPLATFORM): cv.string,
        vol.Optional(CONF_FORECAST): cv.multi_select(DAYS),
        vol.Optional(CONF_HOURLY_FORECAST): cv.multi_select(HOURS),
        vol.Optional(CONF_MONITORED_CONDITIONS, default=None): cv.multi_select(
            ALL_CONDITIONS
        ),          
    }
)



async def async_setup_platform(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Import the platform into a config entry."""
    _LOGGER.warning(
        "Configuration of Pirate Weather sensor in YAML is deprecated "
        "Your existing configuration has been imported into the UI automatically "
        "and can be safely removed from your configuration.yaml file"
    )

    # Define as a sensor platform
    config_entry[PW_PLATFORM] = [PW_PLATFORMS[0]]
    
    # Set as no rounding for compatability
    config_entry[PW_ROUND] = "No"    
    
    hass.async_create_task(
      hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data = config_entry
      )
    )


async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Pirate Weather sensor entities based on a config entry."""
    
    
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    
    name = domain_data[CONF_NAME]
    api_key = domain_data[CONF_API_KEY] 
    weather_coordinator = domain_data[ENTRY_WEATHER_COORDINATOR]
    conditions = domain_data[CONF_MONITORED_CONDITIONS]
    latitude = domain_data[CONF_LATITUDE]
    longitude = domain_data[CONF_LONGITUDE]
    units = domain_data[CONF_UNITS]    
    forecast_days = domain_data[CONF_FORECAST]
    forecast_hours = domain_data[CONF_HOURLY_FORECAST]
    
    # Round Output
    outputRound = domain_data[PW_ROUND]    
    
    sensors: list[PirateWeatherSensor] = []
    
    
    for condition in conditions:
        
        unit_index = {"si": 1, "us": 2, "ca": 3, "uk": 4, "uk2": 5}.get(
            domain_data[CONF_UNITS], 1
        )
        
        # Save units for conversion later
        requestUnits = domain_data[CONF_UNITS]
        
        sensorDescription = SENSOR_TYPES[condition]
        
        if condition in DEPRECATED_SENSOR_TYPES:
            _LOGGER.warning("Monitored condition %s is deprecated", condition)
            
        if not sensorDescription.forecast_mode or "currently" in sensorDescription.forecast_mode:
            unique_id = f"{config_entry.unique_id}-sensor-{condition}"
            sensors.append(PirateWeatherSensor(weather_coordinator, condition, name,  unique_id, forecast_day=None, forecast_hour=None, description=sensorDescription, requestUnits=requestUnits, outputRound=outputRound))
        
      
        if forecast_days is not None and "daily" in sensorDescription.forecast_mode:
            for forecast_day in forecast_days:
                unique_id = f"{config_entry.unique_id}-sensor-{condition}-daily-{forecast_day}"
                sensors.append(
                    PirateWeatherSensor(
                        weather_coordinator, condition, name, unique_id, forecast_day=int(forecast_day), forecast_hour=None, description=sensorDescription, requestUnits=requestUnits, outputRound=outputRound
                    )
                )

        if forecast_hours is not None and "hourly" in sensorDescription.forecast_mode:
            for forecast_h in forecast_hours:
                unique_id = f"{config_entry.unique_id}-sensor-{condition}-hourly-{forecast_h}"
                sensors.append(
                    PirateWeatherSensor(
                        weather_coordinator, condition, name, unique_id, forecast_day=None, forecast_hour=int(forecast_h), description=sensorDescription, requestUnits=requestUnits, outputRound=outputRound
                    )
                )
        
    async_add_entities(sensors)


class PirateWeatherSensor(SensorEntity):
    """Class for an PirateWeather sensor."""

    #_attr_should_poll = False
    _attr_attribution = ATTRIBUTION
    entity_description: PirateWeatherSensorEntityDescription
    
    def __init__(
        self,
        weather_coordinator: WeatherUpdateCoordinator,
        condition: str,
        name: str,
        unique_id,
        forecast_day: int,
        forecast_hour: int,
        description:  PirateWeatherSensorEntityDescription,
        requestUnits: str,
        outputRound: str
    ) -> None:
        """Initialize the sensor."""
        self.client_name = name
                
        description=description
        self.entity_description = description
        self.description=description
        
        self._weather_coordinator = weather_coordinator
        
        self._attr_unique_id = unique_id
        self._attr_name = name
        
        #self._attr_device_info = DeviceInfo(
        #    entry_type=DeviceEntryType.SERVICE,
        #    identifiers={(DOMAIN, unique_id)},
        #    manufacturer=MANUFACTURER,
        #    name=DEFAULT_NAME,
        #)
        
        self.forecast_day = forecast_day
        self.forecast_hour = forecast_hour
        self.requestUnits = requestUnits
        self.outputRound = outputRound
        self.type = condition
        self._icon = None
        self._alerts = None
        
        
        
        self._name = description.name
            
    @property
    def name(self):
        """Return the name of the sensor."""
        if self.forecast_day is not None:
            return f"{self.client_name} {self._name} {self.forecast_day}d"
        if self.forecast_hour is not None:
            return f"{self.client_name} {self._name} {self.forecast_hour}h"
        return f"{self.client_name} {self._name}"
        
        
    @property
    def available(self) -> bool:
        """Return if weather data is available from PirateWeather."""
        return self._weather_coordinator.data is not None

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        unit_key = MAP_UNIT_SYSTEM.get(self.unit_system, "si_unit")
        self._attr_native_unit_of_measurement = getattr(
            self.entity_description, unit_key
        )
        return self._attr_native_unit_of_measurement

    @property
    def unit_system(self):
        """Return the unit system of this entity."""
        return self.requestUnits
        
    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture to use in the frontend, if any."""
        if self._icon is None or "summary" not in self.entity_description.key:
            return None

        if self._icon in CONDITION_PICTURES:
            return CONDITION_PICTURES[self._icon].entity_picture

        return None

    def update_unit_of_measurement(self) -> None:
        """Update units based on unit system."""
        unit_key = MAP_UNIT_SYSTEM.get(self.unit_system, "si_unit")
        self._attr_native_unit_of_measurement = getattr(
            self.entity_description, unit_key
        )
        

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if "summary" in self.type and self._icon in CONDITION_PICTURES:
            return CONDITION_PICTURES[self._icon][1]

        return SENSOR_TYPES[self.type][6]
    
    @property
    def icon(self) -> str | None:
        """Icon to use in the frontend, if any."""
        if (
            "summary" in self.entity_description.key
            and self._icon in CONDITION_PICTURES
        ):
            return CONDITION_PICTURES[self._icon].icon

        return self.entity_description.icon

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self.type == "alerts":
          extraATTR = self._alerts
          extraATTR[ATTR_ATTRIBUTION] = ATTRIBUTION
         
          return extraATTR
        else:
          return {ATTR_ATTRIBUTION: ATTRIBUTION}
          

    @property
    def native_value(self) -> StateType:
        """Return the state of the device."""       
        lookup_type = convert_to_camel(self.type)
        
        self.update_unit_of_measurement()
        
        if  self.type == "alerts":
            data = self._weather_coordinator.data.alerts()
            
            alerts = {}
            if data is None:
                self._alerts = alerts
                return data
    
            multiple_alerts = len(data) > 1
            for i, alert in enumerate(data):
                for attr in ALERTS_ATTRS:
                    if multiple_alerts:
                        dkey = f"{attr}_{i!s}"
                    else:
                        dkey = attr
                    alertsAttr = getattr(alert, attr)
                    
                    # Convert time to string
                    if isinstance(alertsAttr, int):
                      alertsAttr = template_helper.timestamp_local(alertsAttr)
                    
                    alerts[dkey] = alertsAttr
                    
                    
            self._alerts = alerts
            native_val =  len(data)
            
            
        elif self.type == "minutely_summary":
            native_val = getattr(self._weather_coordinator.data.minutely(),"summary", "")
            self._icon = getattr(self._weather_coordinator.data.minutely(),"icon", "")
        elif self.type == "hourly_summary":
            native_val = getattr(self._weather_coordinator.data.hourly(),"summary", "")
            self._icon = getattr(self._weather_coordinator.data.hourly(),"icon", "")
            
        elif self.forecast_hour is not None:
            hourly = self._weather_coordinator.data.hourly()
            if hasattr(hourly, "data"):
                native_val = self.get_state(hourly.data[self.forecast_hour].d)
            else:
                native_val = 0
                
        elif self.type == "daily_summary":
            native_val = getattr(self._weather_coordinator.data.daily(),"summary", "")
            self._icon = getattr(self._weather_coordinator.data.daily(),"icon", "")
            
        elif self.forecast_day is not None:
            daily = self._weather_coordinator.data.daily()
            if hasattr(daily, "data"):
                native_val = self.get_state(daily.data[self.forecast_day].d)
            else:
                native_val = 0
        else:
            currently = self._weather_coordinator.data.currently()
            native_val = self.get_state(currently.d)
        
        #self._state = native_val

        return native_val


    def get_state(self, data):
        """
        Return a new state based on the type.

        If the sensor type is unknown, the current state is returned.
        """
        lookup_type = convert_to_camel(self.type)
        state = data.get(lookup_type)
        
        if state is None:
            return state

        if "summary" in self.type:
            self._icon = getattr(data, "icon", "")

        # If output rounding is requested, round to nearest integer
        if self.outputRound == "Yes":
          roundingVal = 0
        else:
          roundingVal = 1

        # Some state data needs to be rounded to whole values or converted to
        # percentages
        if self.type in ["precip_probability", "cloud_cover", "humidity"]:
            if roundingVal == 0:
              state = int(round(state * 100, roundingVal))
            else:
              state = round(state * 100, roundingVal)
        
        
        # Logic to convert from SI to requsested units for compatability
        # Temps in F
        if self.requestUnits in ["us"]:
          if self.type in [
              "dew_point",
              "temperature",
              "apparent_temperature",
              "temperature_high",
              "temperature_low",
              "apparent_temperature_high",
              "apparent_temperature_low",     
          ]:
              state = ((state * 9 / 5) + 32)
              
        # Km to Miles      
        if self.requestUnits in ["us", "uk", "uk2"]:
          if self.type in [
              "visibility",
              "nearest_storm_distance",    
          ]:
              state = (state * 0.621371)
                      
        # Meters/second to Miles/hour      
        if self.requestUnits in ["us", "uk", "uk2"]:
          if self.type in [
              "wind_speed",
              "wind_gust",    
          ]:
              state =  (state * 2.23694)        
        
        # Meters/second to Km/ hour      
        if self.requestUnits in ["ca"]:
          if self.type in [
              "wind_speed",
              "wind_gust",    
          ]:
              state = (state * 3.6)           
   
   
        
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
            "wind_speed",
            "wind_gust",
        ]:
        
            if roundingVal == 0:
              outState = int(round(state, roundingVal))
            else:
              outState = round(state, roundingVal)
            
        else:
          outState = state
        
        return outState

    async def async_added_to_hass(self) -> None:
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self._weather_coordinator.async_add_listener(self.async_write_ha_state)
        )
            
        
    #async def async_update(self) -> None:
    #    """Get the latest data from PW and updates the states."""
    #    await self._weather_coordinator.async_request_refresh()   
        


def convert_to_camel(data):
    """
    Convert snake case (foo_bar_bat) to camel case (fooBarBat).

    This is not pythonic, but needed for certain situations.
    """
    components = data.split("_")
    capital_components = "".join(x.title() for x in components[1:])
    return f"{components[0]}{capital_components}"


