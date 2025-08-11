"""The Pirate Weather component."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LANGUAGE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODE,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENDPOINT,
    CONF_MODELS,
    CONF_UNITS,
    DEFAULT_ENDPOINT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENTRY_NAME,
    ENTRY_WEATHER_COORDINATOR,
    PLATFORMS,
    PW_PLATFORM,
    PW_PLATFORMS,
    PW_ROUND,
    UPDATE_LISTENER,
)

# from .weather_update_coordinator import WeatherUpdateCoordinator, DarkSkyData
from .weather_update_coordinator import WeatherUpdateCoordinator

CONF_FORECAST = "forecast"
CONF_HOURLY_FORECAST = "hourly_forecast"

_LOGGER = logging.getLogger(__name__)
ATTRIBUTION = "Powered by Pirate Weather"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pirate Weather as config entry."""
    name = entry.data[CONF_NAME]
    api_key = entry.data[CONF_API_KEY]
    latitude = _get_config_value(entry, CONF_LATITUDE)
    longitude = _get_config_value(entry, CONF_LONGITUDE)
    forecast_mode = "daily"
    conditions = _get_config_value(entry, CONF_MONITORED_CONDITIONS)
    units = _get_config_value(entry, CONF_UNITS)
    forecast_days = _get_config_value(entry, CONF_FORECAST)
    forecast_hours = _get_config_value(entry, CONF_HOURLY_FORECAST)
    pw_entity_platform = _get_config_value(entry, PW_PLATFORM)
    pw_entity_rounding = _get_config_value(entry, PW_ROUND)
    scan_interval = _get_config_value(entry, CONF_SCAN_INTERVAL)
    language = _get_config_value(entry, CONF_LANGUAGE)
    endpoint = _get_config_value(entry, CONF_ENDPOINT)
    models = _get_config_value(entry, CONF_MODELS)

    # If scan_interval config value is not configured fall back to the entry data config value
    if not scan_interval:
        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    # If endpoint config value is not configured fall back to the default
    if not endpoint:
        endpoint = DEFAULT_ENDPOINT
        _LOGGER.info("Using default Pirate Weather Endpoint")

    # If latitude or longitude is not configured fall back to the HA location
    if not latitude:
        latitude = hass.config.latitude
    if not longitude:
        longitude = hass.config.longitude

    scan_interval = max(scan_interval, 60)

    # Extract list of int from forecast days/ hours string if present
    # _LOGGER.warning('forecast_days_type: ' + str(type(forecast_days)))

    # _LOGGER.warning(forecast_days)
    if isinstance(forecast_days, str):
        # If empty, set to none
        if forecast_days in {"", "None"}:
            forecast_days = None
        else:
            if forecast_days[0] == "[":
                forecast_days = forecast_days[1:-1].split(",")
            else:
                forecast_days = forecast_days.split(",")
            forecast_days = [int(i) for i in forecast_days]

    if isinstance(forecast_hours, str):
        # If empty, set to none
        if forecast_hours in {"", "None"}:
            forecast_hours = None
        else:
            if forecast_hours[0] == "[":
                forecast_hours = forecast_hours[1:-1].split(",")
            else:
                forecast_hours = forecast_hours.split(",")
            forecast_hours = [int(i) for i in forecast_hours]

    unique_location = f"pw-{latitude}-{longitude}"

    hass.data.setdefault(DOMAIN, {})
    # Create and link weather WeatherUpdateCoordinator
    weather_coordinator = WeatherUpdateCoordinator(
        api_key,
        latitude,
        longitude,
        timedelta(seconds=scan_interval),
        language,
        endpoint,
        units,
        hass,
        entry,
        models,
    )
    hass.data[DOMAIN][unique_location] = weather_coordinator

    # await weather_coordinator.async_refresh()
    await weather_coordinator.async_config_entry_first_refresh()

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
        CONF_HOURLY_FORECAST: forecast_hours,
        PW_PLATFORM: pw_entity_platform,
        PW_ROUND: pw_entity_rounding,
        CONF_SCAN_INTERVAL: scan_interval,
        CONF_LANGUAGE: language,
        CONF_ENDPOINT: endpoint,
        CONF_MODELS: models,
    }

    # Setup platforms
    # If both platforms
    if (PW_PLATFORMS[0] in pw_entity_platform) and (
        PW_PLATFORMS[1] in pw_entity_platform
    ):
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # If only sensor
    elif PW_PLATFORMS[0] in pw_entity_platform:
        await hass.config_entries.async_forward_entry_setups(entry, [PLATFORMS[0]])
    # If only weather
    elif PW_PLATFORMS[1] in pw_entity_platform:
        await hass.config_entries.async_forward_entry_setups(entry, [PLATFORMS[1]])

    update_listener = entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER] = update_listener
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    pw_entity_prevplatform = hass.data[DOMAIN][entry.entry_id][PW_PLATFORM]

    # If both
    if (PW_PLATFORMS[0] in pw_entity_prevplatform) and (
        PW_PLATFORMS[1] in pw_entity_prevplatform
    ):
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # If only sensor
    elif PW_PLATFORMS[0] in pw_entity_prevplatform:
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry, [PLATFORMS[0]]
        )
    # If only Weather
    elif PW_PLATFORMS[1] in pw_entity_prevplatform:
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry, [PLATFORMS[1]]
        )

    _LOGGER.info("Unloading Pirate Weather")

    if unload_ok:
        update_listener = hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER]
        update_listener()

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def _get_config_value(config_entry: ConfigEntry, key: str) -> Any:
    if config_entry.options and key in config_entry.options:
        return config_entry.options[key]
    # Check if key exists
    if config_entry.data and key in config_entry.data:
        return config_entry.data[key]
    return None


def _filter_domain_configs(elements, domain):
    return list(filter(lambda elem: elem["platform"] == domain, elements))
