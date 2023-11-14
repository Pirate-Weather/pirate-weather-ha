"""Constants for WeatherKit."""
from logging import Logger, getLogger


from homeassistant.const import Platform

PLATFORMS = [Platform.SENSOR, Platform.WEATHER]

LOGGER: Logger = getLogger(__package__)

NAME = "Pirate Weather"
DOMAIN = "pirateapple"

MANUFACTURER = "Pirate Weather"

ATTR_CURRENT_WEATHER = "currentWeather"
ATTR_FORECAST_HOURLY = "forecastHourly"
ATTR_FORECAST_DAILY = "forecastDaily"

DEFAULT_NAME = "PirateWeather"
DEFAULT_LANGUAGE = "en"
DEFAULT_UNITS = "us"
DEFAULT_SCAN_INTERVAL = 1200
ATTRIBUTION = "Data provided by Pirate Weather"
MANUFACTURER = "PirateWeather"
CONF_LANGUAGE = "language"
CONF_UNITS = "units"
CONF_FORECAST = "forecast"
CONF_HOURLY_FORECAST = "hourly_forecast"
CONFIG_FLOW_VERSION = 2
ENTRY_NAME = "name"
ENTRY_WEATHER_COORDINATOR = "weather_coordinator"

UPDATE_LISTENER = "update_listener"


PW_PLATFORMS = ["Sensor", "Weather"]
PW_PLATFORM = "pw_platform"
PW_ROUND = "pw_round"


FORECAST_MODE_HOURLY = "hourly"
FORECAST_MODE_DAILY = "daily"

FORECAST_MODES = [
    FORECAST_MODE_HOURLY,
    FORECAST_MODE_DAILY,    
    ]
    
    
DEFAULT_FORECAST_MODE = FORECAST_MODE_DAILY

FORECASTS_HOURLY = "forecasts_hourly"
FORECASTS_DAILY = "forecasts_daily"

ALL_CONDITIONS = {'summary': 'Summary',
                   'icon': 'Icon',
                   'precip_type': 'Precipitation Type',
                   'precip_intensity': 'Precipitation Intensity',
                   'precip_probability': 'Precipitation Probability',
                   'precip_accumulation': 'Precipitation Accumulation',
                   'temperature': 'Temperature',
                   'apparent_temperature': 'Apparent Temperature',
                   'dew_point': 'Dew Point',
                   'humidity': 'Humidity',
                   'wind_speed': 'Wind Speed',
                   'wind_gust': 'Wind Gust',
                   'wind_bearing': 'Wind Bearing',
                   'cloud_cover': 'Cloud Cover',
                   'pressure': 'Pressure',
                   'visibility': 'Visibility',
                   'ozone': 'Ozone',
                   'minutely_summary': 'Minutely Summary',
                   'hourly_summary': 'Hourly Summary',
                   'daily_summary': 'Daily Summary',
                   'temperature_high': 'Temperature High',
                   'temperature_low': 'Temperature Low',
                   'apparent_temperature_high': 'Apparent Temperature High',
                   'apparent_temperature_low': 'Apparent Temperature Low',
                   'precip_intensity_max': 'Precip Intensity Max',
                   'uv_index': 'UV Index',
                   'moon_phase': 'Moon Phase',
                   'sunrise_time': 'Sunrise Time',
                   'sunset_time': 'Sunset Time',
                   'nearest_storm_distance': 'Nearest Storm Distance',         
                   'nearest_storm_bearing': 'Nearest Storm Bearing',
                   'alerts': 'Alerts'                   
                }

LANGUAGES = [
    "af",
    "al",
    "ar",
    "az",
    "bg",
    "ca",
    "cz",
    "da",
    "de",
    "el",
    "en",
    "es",
    "eu",
    "fa",
    "fi",
    "fr",
    "gl",
    "he",
    "hi",
    "hr",
    "hu",
    "id",
    "it",
    "ja",
    "kr",
    "la",
    "lt",
    "mk",
    "nl",
    "no",
    "pl",
    "pt",
    "pt_br",
    "ro",
    "ru",
    "se",
    "sk",
    "sl",
    "sp",
    "sr",
    "sv",
    "th",
    "tr",
    "ua",
    "uk",
    "vi",
    "zh_cn",
    "zh_tw",
    "zu",
]