"""Config flow for Pirate Weather."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any
from uuid import uuid4

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import ClientError
from homeassistant.config_entries import (
    SOURCE_IMPORT,
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
from homeassistant.data_entry_flow import AbortFlow, section
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    ALL_CONDITIONS,
    CONF_ENDPOINT,
    CONF_INSTANCE_ID,
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
from .forecast_config import (
    CONF_FORECAST,
    CONF_HOURLY_FORECAST,
    SensorSettingSelector,
    apply_forecast_controls,
    forecast_form_defaults,
    forecast_offsets,
    forecast_schema,
)
from .sensor import SENSOR_TYPES

ATTRIBUTION = "Powered by Pirate Weather"
_LOGGER = logging.getLogger(__name__)

_ADVANCED = "advanced"
_ADVANCED_SETTINGS = (CONF_MODELS, PW_ROUND, CONF_ENDPOINT, CONF_UNITS)
_BOTH_PLATFORMS = "both"
_SENSOR_SETTINGS = {
    CONF_FORECAST: "",
    CONF_HOURLY_FORECAST: "",
    CONF_MONITORED_CONDITIONS: [],
}


def _platform_selection(platforms: list[str]) -> str:
    """Represent the stored platform list as a single form selection."""
    if all(platform in platforms for platform in PW_PLATFORMS):
        return _BOTH_PLATFORMS
    return (platforms[0] if platforms else PW_PLATFORMS[1]).lower()


def _with_advanced_section(schema: vol.Schema) -> vol.Schema:
    """Group advanced fields in a native, initially collapsed form section."""
    fields = {
        key: value
        for key, value in schema.schema.items()
        if key not in _ADVANCED_SETTINGS
    }
    advanced = {
        key: value for key, value in schema.schema.items() if key in _ADVANCED_SETTINGS
    }
    fields[vol.Required(_ADVANCED)] = section(vol.Schema(advanced), {"collapsed": True})
    return vol.Schema(fields)


def _flatten_form_values(values: dict) -> dict:
    """Keep saved settings flat while accepting the section's nested input."""
    values = dict(values)
    values.update(values.pop(_ADVANCED, {}))
    return values


class _PlatformSelector(SelectSelector):
    """Show one platform choice while retaining the existing stored list format."""

    def __init__(self) -> None:
        super().__init__(
            SelectSelectorConfig(
                options=[platform.lower() for platform in PW_PLATFORMS]
                + [_BOTH_PLATFORMS],
                translation_key="platform",
            )
        )

    def __call__(self, data: Any) -> list[str]:
        """Accept form selections and previously stored platform lists."""
        if isinstance(data, list):
            return cv.multi_select(PW_PLATFORMS)(data)
        selection = super().__call__(data.lower() if isinstance(data, str) else data)
        if selection == _BOTH_PLATFORMS:
            return list(PW_PLATFORMS)
        return [platform for platform in PW_PLATFORMS if platform.lower() == selection]


def _form_values(user_input: dict | None) -> dict | None:
    """Keep platform suggestions in the form's single-selection format."""
    if user_input is None:
        return None
    values = {**user_input, PW_PLATFORM: _platform_selection(user_input[PW_PLATFORM])}
    values.update(forecast_form_defaults(values))
    values.pop(CONF_FORECAST, None)
    values.pop(CONF_HOURLY_FORECAST, None)
    values[_ADVANCED] = {
        key: values.pop(key) for key in _ADVANCED_SETTINGS if key in values
    }
    return values


class _ForecastSummaryMixin:
    """Preview forecast sensor counts without changing current sensor creation."""

    def _finish_configuration(self, values: dict, title: str) -> ConfigFlowResult:
        if (
            self.context.get("source") != SOURCE_IMPORT
            and PW_PLATFORMS[0] in values[PW_PLATFORM]
            and (values.get(CONF_FORECAST) or values.get(CONF_HOURLY_FORECAST))
        ):
            self._pending_data = values
            self._pending_title = title
            return self._forecast_summary_form()
        return self._create_configuration_entry(values, title)

    def _create_configuration_entry(self, values: dict, title: str) -> ConfigFlowResult:
        """Save a reviewed configuration or updated options."""
        return self.async_create_entry(title=title, data=values)

    def _forecast_summary_form(self) -> ConfigFlowResult:
        """Count only conditions supported by each forecast type."""
        values = self._pending_data
        conditions = values.get(CONF_MONITORED_CONDITIONS, [])
        daily_count = len(forecast_offsets(values.get(CONF_FORECAST))) * sum(
            "daily" in SENSOR_TYPES[condition].forecast_mode for condition in conditions
        )
        hourly_count = len(forecast_offsets(values.get(CONF_HOURLY_FORECAST))) * sum(
            "hourly" in SENSOR_TYPES[condition].forecast_mode
            for condition in conditions
        )
        return self.async_show_form(
            step_id="forecast_summary",
            data_schema=vol.Schema({}),
            description_placeholders={
                "daily_count": str(daily_count),
                "hourly_count": str(hourly_count),
                "forecast_total": str(daily_count + hourly_count),
            },
        )

    async def async_step_forecast_summary(self, user_input=None) -> ConfigFlowResult:
        """Save the selected forecasts after the user has reviewed the count."""
        if user_input is not None:
            return self._create_configuration_entry(
                self._pending_data, self._pending_title
            )
        return self._forecast_summary_form()


class PirateWeatherConfigFlow(_ForecastSummaryMixin, ConfigFlow, domain=DOMAIN):
    """Config flow for PirateWeather."""

    VERSION = CONFIG_FLOW_VERSION

    def __init__(self) -> None:
        """Allocate an immutable identity for this new integration instance."""
        super().__init__()
        self._instance_id = uuid4().hex

    def _abort_if_duplicate_configuration(self, values: dict) -> None:
        """Compare effective settings independently of instance identity."""
        for entry in self._async_current_entries(include_ignore=False):
            saved = {**entry.data, **entry.options}
            if (
                saved.get(CONF_LATITUDE) == values[CONF_LATITUDE]
                and saved.get(CONF_LONGITUDE) == values[CONF_LONGITUDE]
                and set(saved.get(PW_PLATFORM, [])) == set(values[PW_PLATFORM])
            ):
                raise AbortFlow("already_configured")

    def _create_configuration_entry(self, values: dict, title: str) -> ConfigFlowResult:
        """Recheck duplicates after API validation and forecast review."""
        self._abort_if_duplicate_configuration(values)
        return super()._create_configuration_entry(values, title)

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
                vol.Optional(
                    CONF_LATITUDE, default=self.hass.config.latitude
                ): cv.latitude,
                vol.Optional(
                    CONF_LONGITUDE, default=self.hass.config.longitude
                ): cv.longitude,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                vol.Required(
                    PW_PLATFORM, default=PW_PLATFORMS[1].lower()
                ): _PlatformSelector(),
                vol.Required(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(
                    LANGUAGES
                ),
                vol.Optional(CONF_MODELS, default=""): str,
                vol.Optional(
                    CONF_MONITORED_CONDITIONS, default=[]
                ): SensorSettingSelector(
                    SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": key, "label": label}
                                for key, label in ALL_CONDITIONS.items()
                            ],
                            multiple=True,
                        )
                    )
                ),
                vol.Optional(PW_ROUND, default="No"): vol.In(["Yes", "No"]),
                vol.Optional(CONF_UNITS, default=DEFAULT_UNITS): vol.In(
                    ["si", "us", "ca", "uk"]
                ),
                vol.Optional(CONF_ENDPOINT, default=DEFAULT_ENDPOINT): str,
            }
        )

        schema = _with_advanced_section(schema.extend(forecast_schema({})))

        if user_input is not None:
            user_input, errors = apply_forecast_controls(
                _flatten_form_values(user_input)
            )
            latitude = user_input[CONF_LATITUDE]
            longitude = user_input[CONF_LONGITUDE]
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

            self._abort_if_duplicate_configuration(user_input)
            await self.async_set_unique_id(f"pw-{self._instance_id}")

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
                return self._finish_configuration(
                    {**user_input, CONF_INSTANCE_ID: self._instance_id}, DEFAULT_NAME
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                schema, _form_values(user_input)
            ),
            errors=errors,
        )

    async def async_step_import(self, import_input=None):
        """Set the config entry up from yaml."""
        config = import_input.copy()

        # Legacy YAML names are no longer part of integration configuration.
        config.pop(CONF_NAME, None)
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


class PirateWeatherOptionsFlow(_ForecastSummaryMixin, OptionsFlow):
    """Handle options."""

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Manage the options."""
        errors = {}
        if user_input is not None:
            user_input = _flatten_form_values(user_input)
            if PW_PLATFORMS[0] not in user_input[PW_PLATFORM]:
                # Hidden fields may be omitted or cleared by the frontend.
                # Retain saved selections when users turn sensors off.
                user_input = {
                    **user_input,
                    **{
                        key: self.config_entry.options.get(
                            key, self.config_entry.data.get(key, default)
                        )
                        for key, default in _SENSOR_SETTINGS.items()
                    },
                }
                user_input.update(
                    forecast_form_defaults(
                        {**self.config_entry.data, **self.config_entry.options}
                    )
                )
            else:
                user_input, errors = apply_forecast_controls(user_input)
            api_key = user_input[CONF_API_KEY].strip()
            user_input = {**user_input, CONF_API_KEY: api_key}
            if not api_key:
                errors[CONF_API_KEY] = "invalid_api_key"
            else:
                try:
                    api_status = await _is_pw_api_online(
                        self.hass,
                        api_key,
                        user_input[CONF_LATITUDE] or self.hass.config.latitude,
                        user_input[CONF_LONGITUDE] or self.hass.config.longitude,
                        user_input[CONF_ENDPOINT] or DEFAULT_ENDPOINT,
                    )
                except ClientError, TimeoutError:
                    errors["base"] = "cannot_connect"
                else:
                    if api_status in (401, 403):
                        errors[CONF_API_KEY] = "invalid_api_key"
                    elif api_status != 200:
                        errors["base"] = "cannot_connect"

            if not errors:
                return self._finish_configuration(user_input, "")

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                self._get_options_schema(), _form_values(user_input)
            ),
            errors=errors,
        )

    def _get_options_schema(self):
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_API_KEY,
                    default=self.config_entry.options.get(
                        CONF_API_KEY, self.config_entry.data[CONF_API_KEY]
                    ),
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
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
                    default=_platform_selection(
                        self.config_entry.options.get(
                            PW_PLATFORM,
                            self.config_entry.data.get(PW_PLATFORM, []),
                        )
                    ),
                ): _PlatformSelector(),
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
                    CONF_MONITORED_CONDITIONS,
                    default=self.config_entry.options.get(
                        CONF_MONITORED_CONDITIONS,
                        self.config_entry.data.get(CONF_MONITORED_CONDITIONS, []),
                    ),
                ): SensorSettingSelector(
                    SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": key, "label": label}
                                for key, label in ALL_CONDITIONS.items()
                            ],
                            multiple=True,
                        )
                    )
                ),
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
        return _with_advanced_section(
            schema.extend(
                forecast_schema({**self.config_entry.data, **self.config_entry.options})
            )
        )


async def _is_pw_api_online(hass, api_key, lat, lon, endpoint):
    forecast_string = (
        endpoint + "/forecast/" + api_key + "/" + str(lat) + "," + str(lon)
    )

    session = async_get_clientsession(hass)
    async with session.get(forecast_string) as resp:
        return resp.status
