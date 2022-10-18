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
    FORECASTS_HOURLY,
    FORECASTS_DAILY,
)

CONF_FORECAST = "forecast"
CONF_HOURLY_FORECAST = "hourly_forecast"

#from .weather_update_coordinator import WeatherUpdateCoordinator, DarkSkyData
from .weather_update_coordinator import WeatherUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
ATTRIBUTION = "Powered by Pirate Weather"


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
    forecast_days = _get_config_value(entry, CONF_FORECAST)
    forecast_hours = _get_config_value(entry, CONF_HOURLY_FORECAST)

    # Extract list of int from forecast days/ hours string if present
    if type(forecast_days) == str:
      # If empty, set to none
      if forecast_days == "":
        forecast_days = None
      else:
        forecast_days = forecast_days.split(",")
        forecast_days = [int(i) for i in forecast_days]
    if type(forecast_hours) == str:
    # If empty, set to none
      if forecast_hours == "":
        forecast_hours = None
      else:
        forecast_hours = forecast_hours.split(",")
        forecast_hours = [int(i) for i in forecast_hours]
      
    unique_location = (f"pw-{latitude}-{longitude}")
    _LOGGER.info("Pirate Weather Init")  
    
    hass.data.setdefault(DOMAIN, {})
    # If coordinator already exists for this API key, we'll use that, otherwise
    # we have to create a new one
    if unique_location in hass.data[DOMAIN]:
      weather_coordinator = hass.data[DOMAIN].get(unique_location)
      #_LOGGER.warning('Old Coordinator')  
    else:
      weather_coordinator = WeatherUpdateCoordinator(api_key, latitude, longitude, hass)
      hass.data[DOMAIN][unique_location] = weather_coordinator    
      #_LOGGER.warning('New Coordinator') 

    await weather_coordinator.async_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = {
        ENTRY_NAME: name,
        ENTRY_WEATHER_COORDINATOR: weather_coordinator,
        CONF_API_KEY: api_key,
        CONF_LATITUDE: latitude,
        CONF_LONGITUDE: longitude,
        CONF_UNITS: units,
        CONF_MONITORED_CONDITIONS: conditions,
        CONF_MODE: forecast_mode,
        CONF_FORECAST: forecast_days,
        CONF_HOURLY_FORECAST: forecast_hours
    }
  
  
    # If no source, then  from GUI
    if "Source" not in entry.data:
      # If no sensors
      if forecast_days is None and forecast_hours is None:
        #_LOGGER.info('GUI-No Sensors') 
        await hass.config_entries.async_forward_entry_setup(entry, PLATFORMS[1])
      elif forecast_mode is None: # If no weather entity is needed
        #_LOGGER.info('GUI-No Weather') 
        await hass.config_entries.async_forward_entry_setup(entry, PLATFORMS[0])
      else:
        #_LOGGER.info('GUI-Both') 
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # If only weather (from YAML) (Check for either forecast_days or forecast_hours
    elif entry.data['Source'] == 'Weather_YAML':
      #_LOGGER.info('YAML Weather') 
      await hass.config_entries.async_forward_entry_setup(entry, PLATFORMS[1])
    # else if sensor  
    elif  entry.data['Source'] == 'Sensor_YAML':
      #_LOGGER.info('YAML Sensor') 
      await hass.config_entries.async_forward_entry_setup(entry, PLATFORMS[0])
    #else both from GUI
    else:
      #_LOGGER.info('Source Other')
      await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    
    update_listener = entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER] = update_listener
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
