"""Config flow for Pirate Weather."""

from __future__ import annotations

import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import ClientError
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODE,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    ALL_CONDITIONS,
    CONF_ENDPOINT,
    CONF_LANGUAGE,
    CONF_MODELS,
    CONF_UNITS,
    CONFIG_FLOW_VERSION,
    DEFAULT_ENDPOINT,
    DEFAULT_FORECAST_MODE,
    DEFAULT_LANGUAGE,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNITS,
    DOMAIN,
    LANGUAGES,
    PW_PLATFORM,
    PW_PLATFORMS,
    PW_PREVPLATFORM,
    PW_ROUND,
)

ATTRIBUTION = "Powered by Pirate Weather"
_LOGGER = logging.getLogger(__name__)

CONF_FORECAST = "forecast"
CONF_HOURLY_FORECAST = "hourly_forecast"


class PirateWeatherConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for PirateWeather."""

    VERSION = CONFIG_FLOW_VERSION

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> PirateWeatherOptionsFlow:
        """Get the options flow for this handler."""
        return PirateWeatherOptionsFlow()

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
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
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                vol.Required(PW_PLATFORM, default=[PW_PLATFORMS[1]]): cv.multi_select(
                    PW_PLATFORMS
                ),
                vol.Required(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(
                    LANGUAGES
                ),
                vol.Optional(CONF_MODELS, default=""): str,
                vol.Optional(CONF_FORECAST, default=""): str,
                vol.Optional(CONF_HOURLY_FORECAST, default=""): str,
                vol.Optional(CONF_MONITORED_CONDITIONS, default=[]): cv.multi_select(
                    ALL_CONDITIONS
                ),
                vol.Optional(PW_ROUND, default="No"): vol.In(["Yes", "No"]),
                vol.Optional(CONF_UNITS, default=DEFAULT_UNITS): vol.In(
                    ["si", "us", "ca", "uk"]
                ),
                vol.Optional(CONF_ENDPOINT, default=DEFAULT_ENDPOINT): str,
            }
        )

        if user_input is not None:
            latitude = user_input[CONF_LATITUDE]
            longitude = user_input[CONF_LONGITUDE]
            forecastMode = "daily"
            forecastPlatform = user_input[PW_PLATFORM]
            entityNamee = user_input[CONF_NAME]
            endpoint = user_input[CONF_ENDPOINT]

            # Convert scan interval to timedelta
            if isinstance(user_input[CONF_SCAN_INTERVAL], str):
                user_input[CONF_SCAN_INTERVAL] = cv.time_period_str(
                    user_input[CONF_SCAN_INTERVAL]
                )

            # Convert scan interval to number of seconds
            if isinstance(user_input[CONF_SCAN_INTERVAL], timedelta):
                user_input[CONF_SCAN_INTERVAL] = user_input[
                    CONF_SCAN_INTERVAL
                ].total_seconds()

            # Unique value includes the location and forcastHours/ forecastDays to seperate WeatherEntity/ Sensor
            # await self.async_set_unique_id(f"pw-{latitude}-{longitude}-{forecastDays}-{forecastHours}-{forecastMode}-{entityNamee}")
            await self.async_set_unique_id(
                f"pw-{latitude}-{longitude}-{forecastPlatform}-{forecastMode}-{entityNamee}"
            )

            self._abort_if_unique_id_configured()

            try:
                api_status = await _is_pw_api_online(
                    self.hass, user_input[CONF_API_KEY], latitude, longitude, endpoint
                )

                if api_status == 403:
                    _LOGGER.warning(
                        "Pirate Weather Setup Error: Invalid API Key, Ensure that you've subscribed to API at https://pirate-weather.apiable.io/"
                    )
                    errors["base"] = (
                        "Invalid API Key, Ensure that you've subscribed to API at https://pirate-weather.apiable.io/"
                    )

            except ClientError:
                _LOGGER.warning(
                    "Pirate Weather Setup Error: API HTTP Error: %s", api_status
                )
                errors["base"] = "API Error: %s", api_status

            if errors:
                _LOGGER.warning(errors)
            else:
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
        if PW_PREVPLATFORM not in config:
            config[PW_PREVPLATFORM] = None
        if PW_ROUND not in config:
            config[PW_ROUND] = "No"
        if CONF_SCAN_INTERVAL not in config:
            config[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL
        if CONF_ENDPOINT not in config:
            config[CONF_ENDPOINT] = DEFAULT_ENDPOINT
        return await self.async_step_user(config)


class PirateWeatherOptionsFlow(OptionsFlow):
    """Handle options."""

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # if self.config_entry.options:
            #  user_input[PW_PREVPLATFORM] = self.config_entry.options[PW_PLATFORM]
            # else:
            # user_input[PW_PREVPLATFORM] = self.hass.data[DOMAIN][entry.entry_id][PW_PLATFORM]
            # self.hass.data[DOMAIN][entry.entry_id][PW_PREVPLATFORM] = self.hass.data[DOMAIN][entry.entry_id][PW_PLATFORM]
            # user_input[PW_PREVPLATFORM] = self.hass.data[DOMAIN][entry.entry_id][PW_PLATFORM]
            # _LOGGER.warning('async_step_init_Options')
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(),
        )

    def _get_options_schema(self):
        return vol.Schema(
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
                        self.config_entry.data.get(
                            CONF_LATITUDE, self.hass.config.latitude
                        ),
                    ),
                ): cv.latitude,
                vol.Optional(
                    CONF_LONGITUDE,
                    default=self.config_entry.options.get(
                        CONF_LONGITUDE,
                        self.config_entry.data.get(
                            CONF_LONGITUDE, self.hass.config.longitude
                        ),
                    ),
                ): cv.longitude,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL,
                        self.config_entry.data.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ),
                ): int,
                vol.Required(
                    PW_PLATFORM,
                    default=self.config_entry.options.get(
                        PW_PLATFORM,
                        self.config_entry.data.get(PW_PLATFORM, []),
                    ),
                ): cv.multi_select(PW_PLATFORMS),
                vol.Optional(
                    CONF_LANGUAGE,
                    default=self.config_entry.options.get(
                        CONF_LANGUAGE,
                        self.config_entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
                    ),
                ): vol.In(LANGUAGES),
                vol.Optional(
                    CONF_MODELS,
                    default=str(
                        self.config_entry.options.get(
                            CONF_MODELS,
                            self.config_entry.data.get(CONF_MODELS, ""),
                        ),
                    ),
                ): str,
                vol.Optional(
                    CONF_FORECAST,
                    default=str(
                        self.config_entry.options.get(
                            CONF_FORECAST,
                            self.config_entry.data.get(CONF_FORECAST, ""),
                        ),
                    ),
                ): str,
                vol.Optional(
                    CONF_HOURLY_FORECAST,
                    default=str(
                        self.config_entry.options.get(
                            CONF_HOURLY_FORECAST,
                            self.config_entry.data.get(CONF_HOURLY_FORECAST, ""),
                        ),
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
                        self.config_entry.options.get(PW_ROUND, "No"),
                    ),
                ): vol.In(["Yes", "No"]),
                vol.Optional(
                    CONF_ENDPOINT,
                    default=str(
                        self.config_entry.options.get(
                            CONF_ENDPOINT,
                            self.config_entry.data.get(CONF_ENDPOINT, DEFAULT_ENDPOINT),
                        ),
                    ),
                ): str,
            }
        )


async def _is_pw_api_online(hass, api_key, lat, lon, endpoint):
    forecastString = endpoint + "/forecast/" + api_key + "/" + str(lat) + "," + str(lon)

    session = async_get_clientsession(hass)
    async with session.get(forecastString) as resp:
        return resp.status
