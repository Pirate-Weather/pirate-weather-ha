"""Consts for the Pirate Weather."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_PRESSURE,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
)
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UV_INDEX,
    Platform,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)

DOMAIN = "pirateweather"
DEFAULT_NAME = "PirateWeather"
DEFAULT_LANGUAGE = "en"
DEFAULT_UNITS = "us"
DEFAULT_SCAN_INTERVAL = 1200
DEFAULT_ENDPOINT = "https://api.pirateweather.net"
ATTRIBUTION = "Data provided by Pirate Weather GUI"
MANUFACTURER = "PirateWeather"
CONF_LANGUAGE = "language"
CONF_UNITS = "units"
CONF_ENDPOINT = "endpoint"
CONF_MODELS = "models"
CONFIG_FLOW_VERSION = 2
ENTRY_NAME = "name"
ENTRY_WEATHER_COORDINATOR = "weather_coordinator"
ATTR_API_PRECIPITATION = "precipitation"
ATTR_API_PRECIPITATION_KIND = "precipitation_kind"
ATTR_API_DATETIME = "datetime"
ATTR_API_DEW_POINT = "dew_point"
ATTR_API_WEATHER = "weather"
ATTR_API_TEMPERATURE = "temperature"
ATTR_API_FEELS_LIKE_TEMPERATURE = "feels_like_temperature"
ATTR_API_WIND_SPEED = "wind_speed"
ATTR_API_WIND_BEARING = "wind_bearing"
ATTR_API_HUMIDITY = "humidity"
ATTR_API_PRESSURE = "pressure"
ATTR_API_CONDITION = "condition"
ATTR_API_CLOUDS = "clouds"
ATTR_API_RAIN = "rain"
ATTR_API_SNOW = "snow"
ATTR_API_UV_INDEX = "uv_index"
ATTR_API_WEATHER_CODE = "weather_code"
ATTR_API_FORECAST = "forecast"
UPDATE_LISTENER = "update_listener"
PLATFORMS = [Platform.SENSOR, Platform.WEATHER]
PW_PLATFORMS = ["Sensor", "Weather"]
PW_PLATFORM = "pw_platform"
PW_PREVPLATFORM = "pw_prevplatform"
PW_ROUND = "pw_round"

ATTR_FORECAST_CLOUD_COVERAGE = "cloud_coverage"
ATTR_FORECAST_HUMIDITY = "humidity"
ATTR_FORECAST_NATIVE_VISIBILITY = "native_visibility"

FORECAST_MODE_HOURLY = "hourly"
FORECAST_MODE_DAILY = "daily"

FORECAST_MODES = [
    FORECAST_MODE_HOURLY,
    FORECAST_MODE_DAILY,
]


DEFAULT_FORECAST_MODE = FORECAST_MODE_DAILY

FORECASTS_HOURLY = "forecasts_hourly"
FORECASTS_DAILY = "forecasts_daily"

ALL_CONDITIONS = {
    "summary": "Summary",
    "icon": "Icon",
    "precip_type": "Precipitation Type",
    "precip_intensity": "Precipitation Intensity",
    "precip_probability": "Precipitation Probability",
    "precip_accumulation": "Precipitation Accumulation",
    "temperature": "Temperature",
    "apparent_temperature": "Apparent Temperature",
    "dew_point": "Dew Point",
    "humidity": "Humidity",
    "wind_speed": "Wind Speed",
    "wind_gust": "Wind Gust",
    "wind_bearing": "Wind Bearing",
    "cloud_cover": "Cloud Cover",
    "pressure": "Pressure",
    "visibility": "Visibility",
    "ozone": "Ozone",
    "minutely_summary": "Minutely Summary",
    "hourly_summary": "Hourly Summary",
    "daily_summary": "Daily Summary",
    "temperature_high": "Temperature High",
    "temperature_low": "Temperature Low",
    "apparent_temperature_high": "Apparent Temperature High",
    "apparent_temperature_low": "Apparent Temperature Low",
    "precip_intensity_max": "Precip Intensity Max",
    "uv_index": "UV Index",
    "moon_phase": "Moon Phase",
    "sunrise_time": "Sunrise Time",
    "sunset_time": "Sunset Time",
    "nearest_storm_distance": "Nearest Storm Distance",
    "nearest_storm_bearing": "Nearest Storm Bearing",
    "alerts": "Alerts",
    "time": "Time",
    "fire_index": "Fire Index",
    "fire_index_max": "Fire Index Max",
    "fire_risk_level": "Fire Risk Level",
    "smoke": "Smoke",
    "smoke_max": "Smoke Max",
    "liquid_accumulation": "Liquid Accumulation",
    "snow_accumulation": "Snow Accumulation",
    "ice_accumulation": "Ice Accumulation",
    "apparent_temperature_high_time": "Daytime High Apparent Temperature Time",
    "apparent_temperature_low_time": "Overnight Low Apparent Temperature Time",
    "temperature_high_time": "Daytime High Temperature Time",
    "temperature_min_time": "Low Temperature Time",
    "hrrr_subh_update_time": "HRRR SubH Update Time",
    "hrrr_0_18_update_time": "HRRR 0-18 Update Time",
    "nbm_update_time": "NBM Update Time",
    "nbm_fire_update_time": "NBM Fire Update Time",
    "hrrr_18_48_update_time": "HRRR 18-48 Update Time",
    "gfs_update_time": "GFS Update Time",
    "gefs_update_time": "GEFS Update Time",
    "current_day_liquid": "Current Day Liquid Accumulation",
    "current_day_snow": "Current Day Snow Accumulation",
    "current_day_ice": "Current Day Ice Accumulation",
}

LANGUAGES = [
    "ar",
    "az",
    "be",
    "bg",
    "bn",
    "bs",
    "ca",
    "cs",
    "cy",
    "da",
    "de",
    "el",
    "en",
    "eo",
    "es",
    "et",
    "fa",
    "fi",
    "fr",
    "ga",
    "gd",
    "he",
    "hi",
    "hr",
    "hu",
    "id",
    "is",
    "it",
    "ja",
    "ka",
    "kn",
    "ko",
    "kw",
    "lv",
    "ml",
    "mr",
    "nl",
    "no",
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
    "vi",
    "x-pig-latin",
    "zh",
    "zh-tw",
]

WEATHER_SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=ATTR_API_WEATHER,
        name="Weather",
    ),
    SensorEntityDescription(
        key=ATTR_API_DEW_POINT,
        name="Dew Point",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ATTR_API_TEMPERATURE,
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ATTR_API_FEELS_LIKE_TEMPERATURE,
        name="Feels like temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ATTR_API_WIND_SPEED,
        name="Wind speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ATTR_API_WIND_BEARING,
        name="Wind bearing",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ATTR_API_HUMIDITY,
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ATTR_API_PRESSURE,
        name="Pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ATTR_API_CLOUDS,
        name="Cloud coverage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ATTR_API_RAIN,
        name="Rain",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ATTR_API_SNOW,
        name="Snow",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ATTR_API_PRECIPITATION_KIND,
        name="Precipitation kind",
    ),
    SensorEntityDescription(
        key=ATTR_API_UV_INDEX,
        name="UV Index",
        native_unit_of_measurement=UV_INDEX,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=ATTR_API_CONDITION,
        name="Condition",
    ),
    SensorEntityDescription(
        key=ATTR_API_WEATHER_CODE,
        name="Weather Code",
    ),
)
FORECAST_SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=ATTR_FORECAST_CONDITION,
        name="Condition",
    ),
    SensorEntityDescription(
        key=ATTR_FORECAST_PRECIPITATION,
        name="Precipitation",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
    ),
    SensorEntityDescription(
        key=ATTR_FORECAST_PRECIPITATION_PROBABILITY,
        name="Precipitation probability",
        native_unit_of_measurement=PERCENTAGE,
    ),
    SensorEntityDescription(
        key=ATTR_FORECAST_PRESSURE,
        name="Pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.PRESSURE,
    ),
    SensorEntityDescription(
        key=ATTR_FORECAST_TEMP,
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    SensorEntityDescription(
        key=ATTR_FORECAST_TEMP_LOW,
        name="Temperature Low",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    SensorEntityDescription(
        key=ATTR_FORECAST_TIME,
        name="Time",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key=ATTR_API_WIND_BEARING,
        name="Wind bearing",
        native_unit_of_measurement=DEGREE,
    ),
    SensorEntityDescription(
        key=ATTR_API_WIND_SPEED,
        name="Wind speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
    ),
    SensorEntityDescription(
        key=ATTR_API_CLOUDS,
        name="Cloud coverage",
        native_unit_of_measurement=PERCENTAGE,
    ),
)
