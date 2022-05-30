"""Config flow for OpenWeatherMap."""
from pyowm import OWM
from pyowm.commons.exceptions import APIRequestError, UnauthorizedError
import voluptuous as vol
import logging

from homeassistant import config_entries
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODE,
    CONF_NAME,
    CONF_MONITORED_CONDITIONS,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

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
)

ATTRIBUTION = "Powered by Pirate Weather"
_LOGGER = logging.getLogger(__name__)


all_conditions = {'Condition 1': 'Condition 1',
                   'Condition 2': 'Condition 2',
                   'Condition 3': 'Condition 3',
                   'Condition 4': 'Condition 4',
                   'Condition 5': 'Condition 5',
                   'Condition 6': 'Condition 6',
                   'Condition 7': 'Condition 7',
                   'Condition 8': 'Condition 8',
                   'Condition 9': 'Condition 9',
                   'Condition 10': 'Condition 10',
                   'Condition 11': 'Condition 11',
                   'Condition 12': 'Condition 12',
                   'Condition 13': 'Condition 13',
                   'Condition 14': 'Condition 14',
                   'Condition 15': 'Condition 15',
                   'Condition 16': 'Condition 16',
                   'Condition 17': 'Condition 17',
                   'Condition 18': 'Condition 18'
                }

#SCHEMA = vol.Schema(
#    {
#        vol.Required(CONF_API_KEY): cv.string,
#        vol.Optional(CONF_LATITUDE): cv.latitude,
#        vol.Optional(CONF_LONGITUDE): cv.longitude,
#        vol.Optional(CONF_MODE, default="hourly"): vol.In(FORECAST_MODES),
#        vol.Optional(CONF_UNITS): vol.In(["auto", "si", "us", "ca", "uk", "uk2"]),
#        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
#    }
#)



class PirateWeatherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for PirateWeather."""

    VERSION = CONFIG_FLOW_VERSION

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return PirateWeatherOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        schema = vol.Schema(
          {
              vol.Required(CONF_API_KEY): str,
              vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
              vol.Optional(
                  CONF_LATITUDE, default=self.hass.config.latitude
              ): cv.latitude,
              vol.Optional(
                  CONF_LONGITUDE, default=self.hass.config.longitude
              ): cv.longitude,
              vol.Required(CONF_MODE, default=DEFAULT_FORECAST_MODE): vol.In(
                  FORECAST_MODES
              ),
              vol.Required(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(
                  LANGUAGES
              ),                
              vol.Optional(CONF_MONITORED_CONDITIONS, default=None):  cv.multi_select(
                  all_conditions
              ),                     
              vol.Optional(CONF_UNITS, default=DEFAULT_UNITS): vol.In(["si", "us", "ca", "uk"]
              ),
          }
        ) 
        
        
        if user_input is not None:
            latitude = user_input[CONF_LATITUDE]
            longitude = user_input[CONF_LONGITUDE]

            _LOGGER.info("PW Unique ID")
            await self.async_set_unique_id(f"{latitude}-{longitude}")            
            self._abort_if_unique_id_configured()

            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
        
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


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
        if CONF_MONITORED_CONDITIONS not in config:
            config[CONF_MONITORED_CONDITIONS] = None    
        if CONF_UNITS not in config:
            config[CONF_UNITS] = DEFAULT_UNITS                    
        return await self.async_step_user(config)

class PirateWeatherOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(),
        )

    def _get_options_schema(self):
        return vol.Schema(
            {
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
            }
        )


async def _is_pw_api_online(hass, api_key, lat, lon):
    return
