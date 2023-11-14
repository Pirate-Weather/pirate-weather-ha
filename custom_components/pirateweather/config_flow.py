"""Adds config flow for WeatherKit."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.core import callback

import voluptuous as vol
from datetime import timedelta

import json

from homeassistant import config_entries, data_entry_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    LOGGER, 
    CONF_LANGUAGE,
    CONFIG_FLOW_VERSION,
    DEFAULT_FORECAST_MODE,
    DEFAULT_LANGUAGE,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    FORECAST_MODES,
    LANGUAGES,
    CONF_UNITS,
    CONF_FORECAST,
    CONF_HOURLY_FORECAST,
    DEFAULT_UNITS,
    ENTRY_NAME,
    ENTRY_WEATHER_COORDINATOR,
    FORECAST_MODES,
    PLATFORMS, 
    MANUFACTURER,    
    FORECASTS_HOURLY,
    FORECASTS_DAILY,
    PW_PLATFORMS,
    PW_PLATFORM,
    PW_ROUND,
    ALL_CONDITIONS,
)

from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODE,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_MONITORED_CONDITIONS,
)


from pirate_weather.api import PirateWeatherAsync
from homeassistant.helpers.aiohttp_client import async_get_clientsession

class PirateWeatherKitFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Pirate Weather."""

    VERSION = CONFIG_FLOW_VERSION


    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PirateWeatherOptionsFlow:
        """Get the options flow for this handler."""
        return PirateWeatherOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> data_entry_flow.FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}
        
        
        # Define data schema with defaults
        DATA_SCHEMA = vol.Schema(
          {
              vol.Required(CONF_API_KEY): str,
              vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
              vol.Optional(
                  CONF_LATITUDE, default=self.hass.config.latitude
              ): cv.latitude,
              vol.Optional(
                  CONF_LONGITUDE, default=self.hass.config.longitude
              ): cv.longitude,
              vol.Optional(
                  CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
              ): int,              
              vol.Required(PW_PLATFORM, default=[PW_PLATFORMS[1]]): cv.multi_select(
                  PW_PLATFORMS
              ),
              vol.Required(CONF_MODE, default=DEFAULT_FORECAST_MODE): vol.In(
                  FORECAST_MODES
              ),
              vol.Required(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(
                  LANGUAGES
              ),                                    
              vol.Optional(CONF_FORECAST, default=""): str,
              vol.Optional(CONF_HOURLY_FORECAST, default=""): str,
              vol.Optional(CONF_MONITORED_CONDITIONS, default=[]):  cv.multi_select(
                  ALL_CONDITIONS
              ),
              vol.Optional(PW_ROUND, default="No"): vol.In(["Yes", "No"]
              ),                
              vol.Optional(CONF_UNITS, default=DEFAULT_UNITS): vol.In(["si", "us", "ca", "uk"]
              ),                             
          }
        ) 
        
        if user_input is not None:           

            latitude = user_input[CONF_LATITUDE]
            longitude = user_input[CONF_LONGITUDE]
            forecastDays = user_input[CONF_FORECAST]
            forecastHours = user_input[CONF_HOURLY_FORECAST]
            forecastMode = user_input[CONF_MODE]
            forecastPlatform = user_input[PW_PLATFORM]
            entityName = user_input[CONF_NAME]

            # Convert scan interval to timedelta
            if isinstance(user_input[CONF_SCAN_INTERVAL], str):
              user_input[CONF_SCAN_INTERVAL] = cv.time_period_str(user_input[CONF_SCAN_INTERVAL])
              
              
            # Convert scan interval to number of seconds
            if isinstance(user_input[CONF_SCAN_INTERVAL], timedelta):
              user_input[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL].total_seconds()                        


            # Check if API call works
            api_status = await self._is_pw_api_online(str(user_input[CONF_API_KEY]), latitude, longitude)
            
            if api_status==True:
            
              return self.async_create_entry(
                title=entityName,
                data=user_input,
              )   

            else:
              LOGGER.warning(api_status.args[1])
              errors["base"] = api_status.args[1]['message']
              
              
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )


    async def async_step_import(self, import_input=None):
        """Set the config entry up from yaml."""
        config = import_input.copy()
        
        if CONF_NAME not in config:
            config[CONF_NAME] = DEFAULT_NAME
        if CONF_LATITUDE not in config:
            config[CONF_LATITUDE] = self.hass.config.latitude
        if CONF_LONGITUDE not in config:
            config[CONF_LONGITUDE] = self.hass.config.longitude
        if CONF_MODE not in config:
            config[CONF_MODE] = DEFAULT_FORECAST_MODE
        if CONF_LANGUAGE not in config:
            config[CONF_LANGUAGE] = DEFAULT_LANGUAGE 
        if CONF_UNITS not in config:
            config[CONF_UNITS] = DEFAULT_UNITS
        if CONF_MONITORED_CONDITIONS not in config:
            config[CONF_MONITORED_CONDITIONS] = []   
        if CONF_FORECAST not in config:
            config[CONF_FORECAST] = ""               
        if CONF_HOURLY_FORECAST not in config:
            config[CONF_HOURLY_FORECAST] = ""
        if CONF_API_KEY not in config:
            config[CONF_API_KEY] = None   
        if PW_PLATFORM not in config:
            config[PW_PLATFORM] = None         
        if PW_ROUND not in config:
            config[PW_ROUND] = "No"                
        if CONF_SCAN_INTERVAL not in config:
            config[CONF_SCAN_INTERVAL] =  DEFAULT_SCAN_INTERVAL                                     
        return await self.async_step_user(config)


    async def _is_pw_api_online(self, key, lat, lon) -> None:
      try:
        client = PirateWeatherAsync(str(key))
        
        forecast = await client.get_forecast(
            lat,
            lon,
            extend=True,  # default `False`
            lang='en',  # default `ENGLISH`
            values_units='si',  # default `auto`
            exclude=[],  # default `[]`,
            timezone='UTC',  # default None - will be set by Pirate Weather API automatically
             client_session= async_get_clientsession(self.hass)  # default aiohttp.ClientSession()
            )
            
        return True
      except Exception as err:
        return err


    
    
class PirateWeatherOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""
    
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry


    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            entry = self.config_entry
            
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
            
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
              {
                vol.Optional(
                    CONF_NAME,
                     default=self.config_entry.options.get(
                       CONF_NAME,
                       self.config_entry.data.get(CONF_NAME, DEFAULT_NAME),
                       ),
                       ): str,      
                vol.Optional(
                    CONF_LATITUDE,
                     default=self.config_entry.options.get(
                       CONF_LATITUDE,
                       self.config_entry.data.get(CONF_LATITUDE, self.hass.config.latitude),
                       ),
                       ): cv.latitude,   
                vol.Optional(
                    CONF_LONGITUDE,
                     default=self.config_entry.options.get(
                       CONF_LONGITUDE,
                       self.config_entry.data.get(CONF_LONGITUDE, self.hass.config.longitude),
                       ),
                       ): cv.longitude,          
                vol.Required(
                    PW_PLATFORM,
                    default=self.config_entry.options.get(
                        PW_PLATFORM,
                        self.config_entry.data.get(PW_PLATFORM, []),
                    ),
                ): cv.multi_select(PW_PLATFORMS),                                                                            
                vol.Optional(
                    CONF_MODE,
                    default=self.config_entry.options.get(
                        CONF_MODE,
                        self.config_entry.data.get(CONF_MODE, DEFAULT_FORECAST_MODE),
                    ),
                ): vol.In(FORECAST_MODES),
                vol.Optional(
                    CONF_LANGUAGE,
                    default=self.config_entry.options.get(
                        CONF_LANGUAGE,
                        self.config_entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
                    ),
                ): vol.In(LANGUAGES),
                vol.Optional(
                    CONF_FORECAST,
                     default=str(self.config_entry.options.get(
                       CONF_FORECAST,
                       self.config_entry.data.get(CONF_FORECAST, "")),
                       ),
                       ): str,  
                vol.Optional(
                    CONF_HOURLY_FORECAST,
                     default=str(self.config_entry.options.get(
                       CONF_HOURLY_FORECAST,
                       self.config_entry.data.get(CONF_HOURLY_FORECAST, "")),
                       ),
                       ): str,           
                vol.Optional(
                    CONF_MONITORED_CONDITIONS,
                     default=self.config_entry.options.get(
                       CONF_MONITORED_CONDITIONS,
                       self.config_entry.data.get(CONF_MONITORED_CONDITIONS, []),
                       ),
                       ): cv.multi_select(ALL_CONDITIONS),        
                vol.Optional(
                    CONF_UNITS,
                     default=self.config_entry.options.get(
                       CONF_UNITS,
                       self.config_entry.data.get(CONF_UNITS, DEFAULT_UNITS),
                       ),
                       ): vol.In(["si", "us", "ca", "uk"]),   
                vol.Optional(
                    PW_ROUND,
                     default=self.config_entry.options.get(
                       PW_ROUND,
                       self.config_entry.data.get(PW_ROUND, "No"),
                       ),
                       ): vol.In(["Yes", "No"]),                                                                                              
              }
            ),
        )

