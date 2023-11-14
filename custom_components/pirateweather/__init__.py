"""Integration for Apple's WeatherKit API."""
from __future__ import annotations
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    LOGGER,
    PLATFORMS,
    CONF_FORECAST,
    CONF_HOURLY_FORECAST,
    PW_PLATFORM,
    PW_PLATFORMS,
    UPDATE_LISTENER
)


from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_SCAN_INTERVAL,
)
    
from .coordinator import PirateWeatherKitDataUpdateCoordinator

from pirate_weather.api import PirateWeatherAsync



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    
    
    hass.data.setdefault(DOMAIN, {})
    
    # Define the coordinator using the client API, http session, and scan interval
    coordinator = PirateWeatherKitDataUpdateCoordinator(
        hass=hass,
        client=PirateWeatherAsync(str(entry.data[CONF_API_KEY])),
        session=async_get_clientsession(hass),
        pw_scan_Int=timedelta(seconds=entry.data[CONF_SCAN_INTERVAL]))
    
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    pw_entity_platform = _get_config_value(entry, PW_PLATFORM)
    
    
    # If both platforms
    if  (PW_PLATFORMS[0] in pw_entity_platform) and (PLATFORMS[1] in pw_entity_platform):
      await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # If only sensor  
    elif PW_PLATFORMS[0] in pw_entity_platform:
      await hass.config_entries.async_forward_entry_setup(entry, PLATFORMS[0])
    # If only weather
    elif PW_PLATFORMS[1] in pw_entity_platform:
      await hass.config_entries.async_forward_entry_setup(entry, PLATFORMS[1])
    
    # Add listener for options flow
    update_listener = entry.add_update_listener(async_update_options)
    
    return True



async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)

  

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    pw_entity_prevplatform = _get_config_value(entry, PW_PLATFORM)

    
    # If both
    if (PW_PLATFORMS[0] in pw_entity_prevplatform) and (PW_PLATFORMS[1] in pw_entity_prevplatform):
      unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # If only sensor
    elif PW_PLATFORMS[0] in pw_entity_prevplatform:
      unload_ok = await hass.config_entries.async_unload_platforms(entry, [PLATFORMS[0]])
    # If only Weather
    elif PW_PLATFORMS[1] in pw_entity_prevplatform:
      unload_ok = await hass.config_entries.async_unload_platforms(entry, [PLATFORMS[1]])
    
    LOGGER.info('Unloading Pirate Weather')
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    
    return unload_ok
    
    

def _get_config_value(config_entry: ConfigEntry, key: str) -> Any:
    if config_entry.options:
        return config_entry.options[key]
    return config_entry.data[key]