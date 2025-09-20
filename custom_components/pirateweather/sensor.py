"""Support for Pirate Weather (Dark Sky Compatable) weather service."""

import datetime
import logging
from dataclasses import dataclass, field
from typing import Literal, NamedTuple

import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.template as template_helper
import voluptuous as vol
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    DEGREE,
    PERCENTAGE,
    UV_INDEX,
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType, StateType

from .const import (
    ALL_CONDITIONS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENTRY_WEATHER_COORDINATOR,
    PW_PLATFORM,
    PW_PLATFORMS,
    PW_PREVPLATFORM,
    PW_ROUND,
)
from .weather_update_coordinator import WeatherUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by Pirate Weather"

CONF_FORECAST = "forecast"
CONF_HOURLY_FORECAST = "hourly_forecast"
CONF_LANGUAGE = "language"
CONF_UNITS = "units"

DEFAULT_LANGUAGE = "en"
DEFAULT_NAME = "Pirate Weather"

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
        si_unit=UnitOfLength.KILOMETERS,
        us_unit=UnitOfLength.MILES,
        ca_unit=UnitOfLength.KILOMETERS,
        uk_unit=UnitOfLength.KILOMETERS,
        uk2_unit=UnitOfLength.MILES,
        suggested_display_precision=2,
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
        suggested_display_precision=0,
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
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        us_unit=UnitOfPrecipitationDepth.INCHES,
        ca_unit=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        uk_unit=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        uk2_unit=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        suggested_display_precision=4,
        icon="mdi:weather-rainy",
        forecast_mode=["currently", "minutely", "hourly", "daily"],
    ),
    "precip_probability": PirateWeatherSensorEntityDescription(
        key="precip_probability",
        name="Precip Probability",
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=PERCENTAGE,
        us_unit=PERCENTAGE,
        ca_unit=PERCENTAGE,
        uk_unit=PERCENTAGE,
        uk2_unit=PERCENTAGE,
        suggested_display_precision=0,
        icon="mdi:water-percent",
        forecast_mode=["currently", "minutely", "hourly", "daily"],
    ),
    "precip_accumulation": PirateWeatherSensorEntityDescription(
        key="precip_accumulation",
        name="Precip Accumulation",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfLength.CENTIMETERS,
        us_unit=UnitOfLength.INCHES,
        ca_unit=UnitOfLength.CENTIMETERS,
        uk_unit=UnitOfLength.CENTIMETERS,
        uk2_unit=UnitOfLength.CENTIMETERS,
        suggested_display_precision=4,
        icon="mdi:weather-snowy",
        forecast_mode=["hourly", "daily"],
    ),
    "liquid_accumulation": PirateWeatherSensorEntityDescription(
        key="liquid_accumulation",
        name="Liquid Accumulation",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfLength.CENTIMETERS,
        us_unit=UnitOfLength.INCHES,
        ca_unit=UnitOfLength.CENTIMETERS,
        uk_unit=UnitOfLength.CENTIMETERS,
        uk2_unit=UnitOfLength.CENTIMETERS,
        suggested_display_precision=4,
        icon="mdi:weather-rainy",
        forecast_mode=["hourly", "daily"],
    ),
    "snow_accumulation": PirateWeatherSensorEntityDescription(
        key="snow_accumulation",
        name="Snow Accumulation",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfLength.CENTIMETERS,
        us_unit=UnitOfLength.INCHES,
        ca_unit=UnitOfLength.CENTIMETERS,
        uk_unit=UnitOfLength.CENTIMETERS,
        uk2_unit=UnitOfLength.CENTIMETERS,
        suggested_display_precision=4,
        icon="mdi:weather-snowy",
        forecast_mode=["hourly", "daily"],
    ),
    "ice_accumulation": PirateWeatherSensorEntityDescription(
        key="ice_accumulation",
        name="Ice Accumulation",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfLength.CENTIMETERS,
        us_unit=UnitOfLength.INCHES,
        ca_unit=UnitOfLength.CENTIMETERS,
        uk_unit=UnitOfLength.CENTIMETERS,
        uk2_unit=UnitOfLength.CENTIMETERS,
        suggested_display_precision=4,
        icon="mdi:weather-snowy-rainy",
        forecast_mode=["hourly", "daily"],
    ),
    "current_day_liquid": PirateWeatherSensorEntityDescription(
        key="current_day_liquid",
        name="Current Day Liquid Accumulation",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfLength.CENTIMETERS,
        us_unit=UnitOfLength.INCHES,
        ca_unit=UnitOfLength.CENTIMETERS,
        uk_unit=UnitOfLength.CENTIMETERS,
        uk2_unit=UnitOfLength.CENTIMETERS,
        suggested_display_precision=4,
        icon="mdi:weather-rainy",
        forecast_mode=["currently"],
    ),
    "current_day_snow": PirateWeatherSensorEntityDescription(
        key="current_day_snow",
        name="Current Day Snow Accumulation",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfLength.CENTIMETERS,
        us_unit=UnitOfLength.INCHES,
        ca_unit=UnitOfLength.CENTIMETERS,
        uk_unit=UnitOfLength.CENTIMETERS,
        uk2_unit=UnitOfLength.CENTIMETERS,
        suggested_display_precision=4,
        icon="mdi:weather-snowy",
        forecast_mode=["currently"],
    ),
    "current_day_ice": PirateWeatherSensorEntityDescription(
        key="current_day_ice",
        name="Current Day Ice Accumulation",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfLength.CENTIMETERS,
        us_unit=UnitOfLength.INCHES,
        ca_unit=UnitOfLength.CENTIMETERS,
        uk_unit=UnitOfLength.CENTIMETERS,
        uk2_unit=UnitOfLength.CENTIMETERS,
        suggested_display_precision=4,
        icon="mdi:weather-snowy-rainy",
        forecast_mode=["currently"],
    ),
    "temperature": PirateWeatherSensorEntityDescription(
        key="temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfTemperature.CELSIUS,
        us_unit=UnitOfTemperature.FAHRENHEIT,
        ca_unit=UnitOfTemperature.CELSIUS,
        uk_unit=UnitOfTemperature.CELSIUS,
        uk2_unit=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        forecast_mode=["currently", "hourly"],
    ),
    "apparent_temperature": PirateWeatherSensorEntityDescription(
        key="apparent_temperature",
        name="Apparent Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfTemperature.CELSIUS,
        us_unit=UnitOfTemperature.FAHRENHEIT,
        ca_unit=UnitOfTemperature.CELSIUS,
        uk_unit=UnitOfTemperature.CELSIUS,
        uk2_unit=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        forecast_mode=["currently", "hourly"],
    ),
    "dew_point": PirateWeatherSensorEntityDescription(
        key="dew_point",
        name="Dew Point",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfTemperature.CELSIUS,
        us_unit=UnitOfTemperature.FAHRENHEIT,
        ca_unit=UnitOfTemperature.CELSIUS,
        uk_unit=UnitOfTemperature.CELSIUS,
        uk2_unit=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "wind_speed": PirateWeatherSensorEntityDescription(
        key="wind_speed",
        name="Wind Speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfSpeed.METERS_PER_SECOND,
        us_unit=UnitOfSpeed.MILES_PER_HOUR,
        ca_unit=UnitOfSpeed.KILOMETERS_PER_HOUR,
        uk_unit=UnitOfSpeed.MILES_PER_HOUR,
        uk2_unit=UnitOfSpeed.MILES_PER_HOUR,
        suggested_display_precision=2,
        icon="mdi:weather-windy",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "wind_bearing": PirateWeatherSensorEntityDescription(
        key="wind_bearing",
        name="Wind Bearing",
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=DEGREE,
        us_unit=DEGREE,
        ca_unit=DEGREE,
        uk_unit=DEGREE,
        uk2_unit=DEGREE,
        suggested_display_precision=0,
        icon="mdi:compass",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "wind_gust": PirateWeatherSensorEntityDescription(
        key="wind_gust",
        name="Wind Gust",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfSpeed.METERS_PER_SECOND,
        us_unit=UnitOfSpeed.MILES_PER_HOUR,
        ca_unit=UnitOfSpeed.KILOMETERS_PER_HOUR,
        uk_unit=UnitOfSpeed.MILES_PER_HOUR,
        uk2_unit=UnitOfSpeed.MILES_PER_HOUR,
        suggested_display_precision=2,
        icon="mdi:weather-windy-variant",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "cloud_cover": PirateWeatherSensorEntityDescription(
        key="cloud_cover",
        name="Cloud Coverage",
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=PERCENTAGE,
        us_unit=PERCENTAGE,
        ca_unit=PERCENTAGE,
        uk_unit=PERCENTAGE,
        uk2_unit=PERCENTAGE,
        suggested_display_precision=0,
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
        suggested_display_precision=0,
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "pressure": PirateWeatherSensorEntityDescription(
        key="pressure",
        name="Pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfPressure.MBAR,
        us_unit=UnitOfPressure.MBAR,
        ca_unit=UnitOfPressure.MBAR,
        uk_unit=UnitOfPressure.MBAR,
        uk2_unit=UnitOfPressure.MBAR,
        suggested_display_precision=2,
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "visibility": PirateWeatherSensorEntityDescription(
        key="visibility",
        name="Visibility",
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfLength.KILOMETERS,
        us_unit=UnitOfLength.MILES,
        ca_unit=UnitOfLength.KILOMETERS,
        uk_unit=UnitOfLength.KILOMETERS,
        uk2_unit=UnitOfLength.MILES,
        suggested_display_precision=2,
        icon="mdi:eye",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "ozone": PirateWeatherSensorEntityDescription(
        key="ozone",
        name="Ozone",
        state_class=SensorStateClass.MEASUREMENT,
        si_unit="DU",
        us_unit="DU",
        ca_unit="DU",
        uk_unit="DU",
        uk2_unit="DU",
        suggested_display_precision=2,
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "fire_index": PirateWeatherSensorEntityDescription(
        key="fire_index",
        name="Fire Index",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:fire",
        forecast_mode=["currently", "hourly"],
    ),
    "fire_risk_level": PirateWeatherSensorEntityDescription(
        key="fire_risk_level",
        name="Fire Risk Level",
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:fire",
        forecast_mode=["currently", "hourly", "daily"],
        options=["Extreme", "Very High", "High", "Moderate", "Low", "N/A"],
    ),
    "fire_index_max": PirateWeatherSensorEntityDescription(
        key="fire_index_max",
        name="Fire Index Max",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:fire",
        forecast_mode=["daily"],
    ),
    "smoke": PirateWeatherSensorEntityDescription(
        key="smoke",
        name="Smoke",
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        us_unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        ca_unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        uk_unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        uk2_unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        suggested_display_precision=2,
        icon="mdi:smoke",
        forecast_mode=["currently", "hourly"],
    ),
    "smoke_max": PirateWeatherSensorEntityDescription(
        key="smoke_max",
        name="Smoke Max",
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        us_unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        ca_unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        uk_unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        uk2_unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        suggested_display_precision=2,
        icon="mdi:smoke",
        forecast_mode=["daily"],
    ),
    "apparent_temperature_max": PirateWeatherSensorEntityDescription(
        key="apparent_temperature_max",
        name="Daily High Apparent Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfTemperature.CELSIUS,
        us_unit=UnitOfTemperature.FAHRENHEIT,
        ca_unit=UnitOfTemperature.CELSIUS,
        uk_unit=UnitOfTemperature.CELSIUS,
        uk2_unit=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        forecast_mode=["daily"],
    ),
    "apparent_temperature_high": PirateWeatherSensorEntityDescription(
        key="apparent_temperature_high",
        name="Daytime High Apparent Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfTemperature.CELSIUS,
        us_unit=UnitOfTemperature.FAHRENHEIT,
        ca_unit=UnitOfTemperature.CELSIUS,
        uk_unit=UnitOfTemperature.CELSIUS,
        uk2_unit=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        forecast_mode=["daily"],
    ),
    "apparent_temperature_high_time": PirateWeatherSensorEntityDescription(
        key="apparent_temperature_high_time",
        name="Daytime High Apparent Temperature Time",
        icon="mdi:clock-time-three-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=["daily"],
    ),
    "apparent_temperature_min": PirateWeatherSensorEntityDescription(
        key="apparent_temperature_min",
        name="Daily Low Apparent Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfTemperature.CELSIUS,
        us_unit=UnitOfTemperature.FAHRENHEIT,
        ca_unit=UnitOfTemperature.CELSIUS,
        uk_unit=UnitOfTemperature.CELSIUS,
        uk2_unit=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        forecast_mode=["daily"],
    ),
    "apparent_temperature_low": PirateWeatherSensorEntityDescription(
        key="apparent_temperature_low",
        name="Overnight Low Apparent Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfTemperature.CELSIUS,
        us_unit=UnitOfTemperature.FAHRENHEIT,
        ca_unit=UnitOfTemperature.CELSIUS,
        uk_unit=UnitOfTemperature.CELSIUS,
        uk2_unit=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        forecast_mode=["daily"],
    ),
    "apparent_temperature_low_time": PirateWeatherSensorEntityDescription(
        key="apparent_temperature_low_time",
        name="Overnight Low Apparent Temperature Time",
        icon="mdi:clock-time-three-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=["daily"],
    ),
    "temperature_max": PirateWeatherSensorEntityDescription(
        key="temperature_max",
        name="Daily High Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfTemperature.CELSIUS,
        us_unit=UnitOfTemperature.FAHRENHEIT,
        ca_unit=UnitOfTemperature.CELSIUS,
        uk_unit=UnitOfTemperature.CELSIUS,
        uk2_unit=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        forecast_mode=["daily"],
    ),
    "temperature_high": PirateWeatherSensorEntityDescription(
        key="temperature_high",
        name="Daytime High Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfTemperature.CELSIUS,
        us_unit=UnitOfTemperature.FAHRENHEIT,
        ca_unit=UnitOfTemperature.CELSIUS,
        uk_unit=UnitOfTemperature.CELSIUS,
        uk2_unit=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        forecast_mode=["daily"],
    ),
    "temperature_high_time": PirateWeatherSensorEntityDescription(
        key="temperature_high_time",
        name="Daytime High Temperature Time",
        icon="mdi:clock-time-three-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=["daily"],
    ),
    "temperature_min": PirateWeatherSensorEntityDescription(
        key="temperature_min",
        name="Daily Low Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfTemperature.CELSIUS,
        us_unit=UnitOfTemperature.FAHRENHEIT,
        ca_unit=UnitOfTemperature.CELSIUS,
        uk_unit=UnitOfTemperature.CELSIUS,
        uk2_unit=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        forecast_mode=["daily"],
    ),
    "temperature_min_time": PirateWeatherSensorEntityDescription(
        key="temperature_min_time",
        name="Daily Low Temperature Time",
        icon="mdi:clock-time-three-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=["daily"],
    ),
    "temperature_low": PirateWeatherSensorEntityDescription(
        key="temperature_low",
        name="Overnight Low Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfTemperature.CELSIUS,
        us_unit=UnitOfTemperature.FAHRENHEIT,
        ca_unit=UnitOfTemperature.CELSIUS,
        uk_unit=UnitOfTemperature.CELSIUS,
        uk2_unit=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        forecast_mode=["daily"],
    ),
    "precip_intensity_max": PirateWeatherSensorEntityDescription(
        key="precip_intensity_max",
        name="Daily Max Precip Intensity",
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        us_unit=UnitOfPrecipitationDepth.INCHES,
        ca_unit=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        uk_unit=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        uk2_unit=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        suggested_display_precision=2,
        icon="mdi:thermometer",
        forecast_mode=["daily"],
    ),
    "uv_index": PirateWeatherSensorEntityDescription(
        key="uv_index",
        name="UV Index",
        state_class=SensorStateClass.MEASUREMENT,
        si_unit=UV_INDEX,
        us_unit=UV_INDEX,
        ca_unit=UV_INDEX,
        uk_unit=UV_INDEX,
        uk2_unit=UV_INDEX,
        suggested_display_precision=2,
        icon="mdi:weather-sunny",
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "moon_phase": PirateWeatherSensorEntityDescription(
        key="moon_phase",
        name="Moon Phase",
        suggested_display_precision=2,
        icon="mdi:weather-night",
        forecast_mode=["daily"],
    ),
    "sunrise_time": PirateWeatherSensorEntityDescription(
        key="sunrise_time",
        name="Sunrise",
        icon="mdi:white-balance-sunny",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=["daily"],
    ),
    "sunset_time": PirateWeatherSensorEntityDescription(
        key="sunset_time",
        name="Sunset",
        icon="mdi:weather-night",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=["daily"],
    ),
    "alerts": PirateWeatherSensorEntityDescription(
        key="alerts",
        name="Alerts",
        icon="mdi:alert-circle-outline",
        forecast_mode=[],
    ),
    "time": PirateWeatherSensorEntityDescription(
        key="time",
        name="Time",
        icon="mdi:clock-time-three-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=["currently", "hourly", "daily"],
    ),
    "hrrr_subh_update_time": PirateWeatherSensorEntityDescription(
        key="hrrr_subh",
        name="HRRR SubHourly Update Time",
        icon="mdi:clock-time-three-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=[],
    ),
    "hrrr_0_18_update_time": PirateWeatherSensorEntityDescription(
        key="hrrr_0-18",
        name="HRRR 0-18 Update Time",
        icon="mdi:clock-time-three-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=[],
    ),
    "nbm_update_time": PirateWeatherSensorEntityDescription(
        key="nbm",
        name="NBM Update Time",
        icon="mdi:clock-time-three-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=[],
    ),
    "nbm_fire_update_time": PirateWeatherSensorEntityDescription(
        key="nbm_fire",
        name="NBM Fire Update Time",
        icon="mdi:clock-time-three-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=[],
    ),
    "hrrr_18_48_update_time": PirateWeatherSensorEntityDescription(
        key="hrrr_18-48",
        name="HRRR 18-48 Update Time",
        icon="mdi:clock-time-three-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=[],
    ),
    "gfs_update_time": PirateWeatherSensorEntityDescription(
        key="gfs",
        name="GFS Update Time",
        icon="mdi:clock-time-three-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        forecast_mode=[],
    ),
    "gefs_update_time": PirateWeatherSensorEntityDescription(
        key="gefs",
        name="GEFS  Update Time",
        icon="mdi:clock-time-three-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
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

ALLOWED_UNITS = ["si", "us", "ca", "uk", "uk2"]

ALERTS_ATTRS = ["time", "description", "expires", "severity", "uri", "regions", "title"]

HOURS = list(range(168))
DAYS = list(range(7))

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
        vol.Optional(PW_PLATFORM): cv.multi_select(PW_PLATFORMS),
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
            DOMAIN, context={"source": SOURCE_IMPORT}, data=config_entry
        )
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
    conditions = domain_data[CONF_MONITORED_CONDITIONS]
    forecast_days = domain_data[CONF_FORECAST]
    forecast_hours = domain_data[CONF_HOURLY_FORECAST]

    # Round Output
    outputRound = domain_data[PW_ROUND]

    sensors: list[PirateWeatherSensor] = []

    for condition in conditions:
        # Save units for conversion later
        requestUnits = domain_data[CONF_UNITS]

        sensorDescription = SENSOR_TYPES[condition]

        if condition in DEPRECATED_SENSOR_TYPES:
            _LOGGER.warning("Monitored condition %s is deprecated", condition)

        if (
            not sensorDescription.forecast_mode
            or "currently" in sensorDescription.forecast_mode
        ):
            unique_id = f"{config_entry.unique_id}-sensor-{condition}"
            sensors.append(
                PirateWeatherSensor(
                    weather_coordinator,
                    condition,
                    name,
                    unique_id,
                    forecast_day=None,
                    forecast_hour=None,
                    description=sensorDescription,
                    requestUnits=requestUnits,
                    outputRound=outputRound,
                )
            )

        if forecast_days is not None and "daily" in sensorDescription.forecast_mode:
            for forecast_day in forecast_days:
                unique_id = (
                    f"{config_entry.unique_id}-sensor-{condition}-daily-{forecast_day}"
                )
                sensors.append(
                    PirateWeatherSensor(
                        weather_coordinator,
                        condition,
                        name,
                        unique_id,
                        forecast_day=int(forecast_day),
                        forecast_hour=None,
                        description=sensorDescription,
                        requestUnits=requestUnits,
                        outputRound=outputRound,
                    )
                )

        if forecast_hours is not None and "hourly" in sensorDescription.forecast_mode:
            for forecast_h in forecast_hours:
                unique_id = (
                    f"{config_entry.unique_id}-sensor-{condition}-hourly-{forecast_h}"
                )
                sensors.append(
                    PirateWeatherSensor(
                        weather_coordinator,
                        condition,
                        name,
                        unique_id,
                        forecast_day=None,
                        forecast_hour=int(forecast_h),
                        description=sensorDescription,
                        requestUnits=requestUnits,
                        outputRound=outputRound,
                    )
                )

    async_add_entities(sensors)


class PirateWeatherSensor(SensorEntity):
    """Class for an Pirate Weather sensor."""

    # _attr_should_poll = False
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
        description: PirateWeatherSensorEntityDescription,
        requestUnits: str,
        outputRound: str,
    ) -> None:
        """Initialize the sensor."""
        self.client_name = name

        self.entity_description = description
        self.description = description

        self._weather_coordinator = weather_coordinator

        self._attr_unique_id = unique_id
        self._attr_name = name

        # self._attr_device_info = DeviceInfo(
        #    entry_type=DeviceEntryType.SERVICE,
        #    identifiers={(DOMAIN, unique_id)},
        #    manufacturer=MANUFACTURER,
        #    name=DEFAULT_NAME,
        # )

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
        """Return if weather data is available from Pirate Weather."""
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
        else:
            extraATTR = {ATTR_ATTRIBUTION: ATTRIBUTION}
        return extraATTR

    @property
    def native_value(self) -> StateType:
        """Return the state of the device."""
        self.update_unit_of_measurement()

        if self.type == "alerts":
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
            native_val = len(data)

        elif self.type in [
            "hrrr_subh_update_time",
            "hrrr_0_18_update_time",
            "nbm_update_time",
            "nbm_fire_update_time",
            "hrrr_18_48_update_time",
            "gfs_update_time",
            "gefs_update_time",
        ]:
            try:
                flags = self._weather_coordinator.data.flags()
                model_time_string = flags.sourceTimes[self.entity_description.key]
                native_val = datetime.datetime.strptime(
                    model_time_string[0:-1], "%Y-%m-%d %H"
                ).replace(tzinfo=datetime.UTC)
            except KeyError:
                native_val = None

        elif self.type == "minutely_summary":
            native_val = getattr(
                self._weather_coordinator.data.minutely(), "summary", ""
            )
            self._icon = getattr(self._weather_coordinator.data.minutely(), "icon", "")
        elif self.type == "hourly_summary":
            native_val = getattr(self._weather_coordinator.data.hourly(), "summary", "")
            self._icon = getattr(self._weather_coordinator.data.hourly(), "icon", "")

        elif self.forecast_hour is not None:
            hourly = self._weather_coordinator.data.hourly()
            if hasattr(hourly, "data"):
                native_val = self.get_state(hourly.data[self.forecast_hour].d)
            else:
                native_val = 0

        elif self.type == "daily_summary":
            native_val = getattr(self._weather_coordinator.data.daily(), "summary", "")
            self._icon = getattr(self._weather_coordinator.data.daily(), "icon", "")

        elif self.forecast_day is not None:
            daily = self._weather_coordinator.data.daily()
            if hasattr(daily, "data"):
                native_val = self.get_state(daily.data[self.forecast_day].d)
            else:
                native_val = 0
        else:
            currently = self._weather_coordinator.data.currently()
            native_val = self.get_state(currently.d)

        # self._state = native_val

        return native_val

    def get_state(self, data):
        """Return a new state based on the type.

        If the sensor type is unknown, the current state is returned.
        """

        if self.type == "fire_risk_level":
            if self.forecast_hour is not None:
                state = data.get("fireIndex")
            elif self.forecast_day is not None:
                state = data.get("fireIndexMax")
            else:
                state = data.get("fireIndex")
        else:
            lookup_type = convert_to_camel(self.type)
            state = data.get(lookup_type)

            # If the sensor is numeric and the data is -999 set return None instead of -999
            if isinstance(state, (int, float)) and state == -999:
                return None

        if state is None:
            return state

        if "summary" in self.type:
            self._icon = getattr(data, "icon", "")

        # If output rounding is requested, round to nearest integer
        if self.outputRound == "Yes":
            roundingVal = 0
            roundingPrecip = 2
        else:
            roundingVal = 2
            roundingPrecip = 4

        # Some state data needs to be rounded to whole values or converted to
        # percentages
        if self.type in ["precip_probability", "cloud_cover", "humidity"]:
            state = int(state * 100)

        # Convert unix times to datetimes times
        if self.type in [
            "temperature_high_time",
            "temperature_min_time",
            "apparent_temperature_high_time",
            "apparent_temperature_low_time",
            "sunrise_time",
            "sunset_time",
            "time",
        ]:
            outState = datetime.datetime.fromtimestamp(state, datetime.UTC)

        elif self.type == "fire_risk_level":
            outState = fire_index(state)
        elif self.type in [
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
            "pressure",
            "ozone",
            "fire_index",
            "fire_index_max",
            "uv_index",
            "wind_speed",
            "wind_gust",
            "visibility",
            "nearest_storm_distance",
            "smoke",
            "smoke_max",
        ]:
            if roundingVal == 0:
                outState = int(round(state, roundingVal))
            else:
                outState = round(state, roundingVal)

        elif self.type in [
            "precip_accumulation",
            "liquid_accumulation",
            "snow_accumulation",
            "ice_accumulation",
            "precip_intensity",
            "precip_intensity_max",
            "current_day_liquid",
            "current_day_snow",
            "current_day_ice",
        ]:
            outState = round(state, roundingPrecip)

        else:
            outState = state

        return outState

    async def async_added_to_hass(self) -> None:
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self._weather_coordinator.async_add_listener(self.async_write_ha_state)
        )

    # async def async_update(self) -> None:
    #    """Get the latest data from PW and updates the states."""
    #    await self._weather_coordinator.async_request_refresh()


def convert_to_camel(data):
    """Convert snake case (foo_bar_bat) to camel case (fooBarBat).

    This is not pythonic, but needed for certain situations.
    """
    components = data.split("_")
    capital_components = "".join(x.title() for x in components[1:])
    return f"{components[0]}{capital_components}"


def fire_index(fire_index):
    """Convert numeric fire index to a textual value."""

    if fire_index == -999:
        outState = "N/A"
    elif fire_index >= 30:
        outState = "Extreme"
    elif fire_index >= 20:
        outState = "Very High"
    elif fire_index >= 10:
        outState = "High"
    elif fire_index >= 5:
        outState = "Moderate"
    else:
        outState = "Low"

    return outState
