"""The Pirate Weather component."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from pyowm import OWM
import forecastio
from pyowm.utils.config import get_default_config

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry

from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODE,
    CONF_NAME,
    CONF_MONITORED_CONDITIONS,
)
from homeassistant.core import HomeAssistant

from .const import (
    CONF_LANGUAGE,
    CONFIG_FLOW_VERSION,
    DOMAIN,
    DEFAULT_FORECAST_MODE,
    ENTRY_NAME,
    ENTRY_WEATHER_COORDINATOR,
    FORECAST_MODES,
    PLATFORMS,
    UPDATE_LISTENER,
    CONF_UNITS,
    DEFAULT_UNITS,
    DEFAULT_NAME,
)

#from .weather_update_coordinator import WeatherUpdateCoordinator, DarkSkyData
from .weather_update_coordinator import WeatherUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
ATTRIBUTION = "Powered by Pirate Weather"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the PirateWeather component."""
    _LOGGER.info("PW Setup A")
    hass.data.setdefault(DOMAIN, {})

    weather_configs = _filter_domain_configs(config.get("weather", []), DOMAIN)
    #sensor_configs = _filter_domain_configs(config.get("sensor", []), DOMAIN)

    #_import_configs(hass, weather_configs + sensor_configs)
    _import_configs(hass, weather_configs)
    _LOGGER.info("PW Setup B")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pirate Weather as config entry."""
    name = entry.data[CONF_NAME]
    api_key = entry.data[CONF_API_KEY]
    latitude = entry.data.get(CONF_LATITUDE, hass.config.latitude)
    longitude = entry.data.get(CONF_LONGITUDE, hass.config.longitude)
    forecast_mode = _get_config_value(entry, CONF_MODE)
    language = _get_config_value(entry, CONF_LANGUAGE)
    conditions = _get_config_value(entry, CONF_MONITORED_CONDITIONS)
    units = _get_config_value(entry, CONF_UNITS)

    _LOGGER.info("PW CONF_MODE_I")
    _LOGGER.info(forecast_mode)
    _LOGGER.info(entry)
    _LOGGER.info(CONF_MODE)
    
#    owm = OWM(api_key, config_dict).weather_manager()
#    weather_coordinator = WeatherUpdateCoordinator(
#        owm, latitude, longitude, forecast_mode, hass
#    )

    #dark_sky = DarkSkyData(api_key, latitude, longitude, units, hass)
    #weather_coordinator = WeatherUpdateCoordinator(dark_sky, latitude, longitude, forecast_mode, hass)
    weather_coordinator = WeatherUpdateCoordinator(api_key, latitude, longitude, units, forecast_mode, hass)

    #_LOGGER.info("PW_Init_A")
    #await weather_coordinator.async_config_entry_first_refresh()
    await weather_coordinator.async_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        ENTRY_NAME: name,
        ENTRY_WEATHER_COORDINATOR: weather_coordinator,
        CONF_API_KEY: api_key,
        CONF_LATITUDE: latitude,
        CONF_LONGITUDE: longitude,
        CONF_UNITS: units,
        CONF_MONITORED_CONDITIONS: conditions,
        CONF_MODE: forecast_mode
    }

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    update_listener = entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER] = update_listener
    _LOGGER.info("PW_Init_B")
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        update_listener = hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER]
        update_listener()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def _get_config_value(config_entry: ConfigEntry, key: str) -> Any:
    if config_entry.options:
        return config_entry.options[key]
    return config_entry.data[key]


def _filter_domain_configs(elements, domain):
    return list(filter(lambda elem: elem["platform"] == domain, elements))
    
def _import_configs(hass, configs):
    for config in configs:
        _LOGGER.info("Importing PW Config!")
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=config,
            )
        )