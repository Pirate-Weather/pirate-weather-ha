"""Support for the Pirate Weather service."""

from __future__ import annotations

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_EXCEPTIONAL,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    PLATFORM_SCHEMA,
    Forecast,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODE,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.util.dt import utc_from_timestamp

from .const import (
    CONF_UNITS,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENTRY_WEATHER_COORDINATOR,
    FORECAST_MODES,
    MANUFACTURER,
    PW_PLATFORM,
    PW_PLATFORMS,
    PW_PREVPLATFORM,
    PW_ROUND,
)
from .values import valid_number
from .weather_update_coordinator import WeatherUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by Pirate Weather"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
        vol.Optional(PW_PLATFORM): cv.string,
        vol.Optional(PW_PREVPLATFORM): cv.string,
        vol.Optional(CONF_MODE, default="hourly"): vol.In(FORECAST_MODES),
        vol.Optional(CONF_UNITS): vol.In(["si", "us", "ca", "uk", "uk2"]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    }
)

MAP_CONDITION = {
    "clear-day": ATTR_CONDITION_SUNNY,
    "clear-night": ATTR_CONDITION_CLEAR_NIGHT,
    "rain": ATTR_CONDITION_RAINY,
    "snow": ATTR_CONDITION_SNOWY,
    "sleet": ATTR_CONDITION_SNOWY_RAINY,
    "wind": ATTR_CONDITION_WINDY,
    "fog": ATTR_CONDITION_FOG,
    "cloudy": ATTR_CONDITION_CLOUDY,
    "partly-cloudy-day": ATTR_CONDITION_PARTLYCLOUDY,
    "partly-cloudy-night": ATTR_CONDITION_PARTLYCLOUDY,
    "hail": ATTR_CONDITION_HAIL,
    "thunderstorm": ATTR_CONDITION_LIGHTNING,
    "tornado": ATTR_CONDITION_EXCEPTIONAL,
    "none": ATTR_CONDITION_EXCEPTIONAL,
    "mixed": ATTR_CONDITION_SNOWY_RAINY,
}

WEATHER_UNITS = {
    "si": {
        "temperature": UnitOfTemperature.CELSIUS,
        "wind_speed": UnitOfSpeed.METERS_PER_SECOND,
        "pressure": UnitOfPressure.MBAR,
        "precipitation": UnitOfPrecipitationDepth.MILLIMETERS,
        "visibility": UnitOfLength.KILOMETERS,
    },
    "us": {
        "temperature": UnitOfTemperature.FAHRENHEIT,
        "wind_speed": UnitOfSpeed.MILES_PER_HOUR,
        "pressure": UnitOfPressure.MBAR,
        "precipitation": UnitOfPrecipitationDepth.INCHES,
        "visibility": UnitOfLength.MILES,
    },
    "ca": {
        "temperature": UnitOfTemperature.CELSIUS,
        "wind_speed": UnitOfSpeed.KILOMETERS_PER_HOUR,
        "pressure": UnitOfPressure.MBAR,
        "precipitation": UnitOfPrecipitationDepth.MILLIMETERS,
        "visibility": UnitOfLength.KILOMETERS,
    },
    "uk": {
        "temperature": UnitOfTemperature.CELSIUS,
        "wind_speed": UnitOfSpeed.MILES_PER_HOUR,
        "pressure": UnitOfPressure.MBAR,
        "precipitation": UnitOfPrecipitationDepth.MILLIMETERS,
        "visibility": UnitOfLength.MILES,
    },
    "uk2": {
        "temperature": UnitOfTemperature.CELSIUS,
        "wind_speed": UnitOfSpeed.MILES_PER_HOUR,
        "pressure": UnitOfPressure.MBAR,
        "precipitation": UnitOfPrecipitationDepth.MILLIMETERS,
        "visibility": UnitOfLength.MILES,
    },
}

CONF_UNITS = "units"

DEFAULT_NAME = "Pirate Weather"


async def async_setup_platform(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Import the platform into a config entry."""
    _LOGGER.warning(
        "Configuration of Pirate Weather (weather entity) in YAML is deprecated "
        "Your existing configuration has been imported into the UI automatically "
        "and can be safely removed from your configuration.yaml file"
    )

    # Add source to config
    config_entry[PW_PLATFORM] = [PW_PLATFORMS[1]]

    # Set as no rounding for compatability
    config_entry[PW_ROUND] = "No"

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=config_entry
        )
    )


def _number(value, digits=None, scale=1):
    """Return a valid measurement, optionally scaled and rounded."""
    if not valid_number(value):
        return None
    value *= scale
    return round(value, digits) if digits is not None else value


def _get_precip(forecast, unit_system: str) -> float | None:
    """Get and convert precipitation accumulation."""
    return _number(
        forecast.d.get("precipAccumulation"), scale=1 if unit_system == "us" else 10
    )


def _map_daily_forecast(forecast, unit_system) -> Forecast:
    precip = _get_precip(forecast, unit_system)
    return {
        "datetime": utc_from_timestamp(forecast.d.get("time")).isoformat(),
        "condition": MAP_CONDITION.get(forecast.d.get("icon")),
        "native_temperature": _number(forecast.d.get("temperatureHigh")),
        "native_templow": _number(forecast.d.get("temperatureLow")),
        "native_precipitation": precip,
        "precipitation_probability": _number(
            forecast.d.get("precipProbability"), 0, scale=100
        ),
        "humidity": _number(forecast.d.get("humidity"), 2, scale=100),
        "cloud_coverage": _number(forecast.d.get("cloudCover"), 0, scale=100),
        "native_wind_speed": _number(forecast.d.get("windSpeed"), 2),
        "native_wind_gust_speed": _number(forecast.d.get("windGust"), 2),
        "wind_bearing": _number(forecast.d.get("windBearing"), 0),
        "native_dew_point": _number(forecast.d.get("dewPoint")),
        "native_pressure": _number(forecast.d.get("pressure")),
        "uv_index": _number(forecast.d.get("uvIndex"), 2),
    }


def _map_day_night_forecast(
    forecast, unit_system, is_day: bool | None = None
) -> Forecast:
    precip = _get_precip(forecast, unit_system)
    # If caller provided an `is_day` hint (we'll pass parity from the list),
    # prefer that. Otherwise fall back to a minimal inference from the icon.
    is_daytime: bool | None = is_day
    if is_daytime is None:
        icon = forecast.d.get("icon")
        if isinstance(icon, str):
            if "night" in icon:
                is_daytime = False
            elif "day" in icon:
                is_daytime = True

    return {
        "is_daytime": is_daytime,
        "datetime": utc_from_timestamp(forecast.d.get("time")).isoformat(),
        "condition": MAP_CONDITION.get(forecast.d.get("icon")),
        "native_temperature": _number(forecast.d.get("temperature")),
        "native_apparent_temperature": _number(forecast.d.get("apparentTemperature")),
        "native_dew_point": _number(forecast.d.get("dewPoint")),
        "native_pressure": _number(forecast.d.get("pressure")),
        "native_wind_speed": _number(forecast.d.get("windSpeed"), 2),
        "wind_bearing": _number(forecast.d.get("windBearing"), 0),
        "native_wind_gust_speed": _number(forecast.d.get("windGust"), 2),
        "humidity": _number(forecast.d.get("humidity"), 2, scale=100),
        "native_precipitation": precip,
        "precipitation_probability": _number(
            forecast.d.get("precipProbability"), 0, scale=100
        ),
        "cloud_coverage": _number(forecast.d.get("cloudCover"), 0, scale=100),
        "uv_index": _number(forecast.d.get("uvIndex"), 2),
    }


def _map_hourly_forecast(forecast, unit_system) -> Forecast:
    precip = _get_precip(forecast, unit_system)
    return {
        "datetime": utc_from_timestamp(forecast.d.get("time")).isoformat(),
        "condition": MAP_CONDITION.get(forecast.d.get("icon")),
        "native_temperature": _number(forecast.d.get("temperature")),
        "native_apparent_temperature": _number(forecast.d.get("apparentTemperature")),
        "native_dew_point": _number(forecast.d.get("dewPoint")),
        "native_pressure": _number(forecast.d.get("pressure")),
        "native_wind_speed": _number(forecast.d.get("windSpeed"), 2),
        "wind_bearing": _number(forecast.d.get("windBearing"), 0),
        "native_wind_gust_speed": _number(forecast.d.get("windGust"), 2),
        "humidity": _number(forecast.d.get("humidity"), 2, scale=100),
        "native_precipitation": precip,
        "precipitation_probability": _number(
            forecast.d.get("precipProbability"), 0, scale=100
        ),
        "cloud_coverage": _number(forecast.d.get("cloudCover"), 0, scale=100),
        "uv_index": _number(forecast.d.get("uvIndex"), 2),
    }


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pirate Weather entity based on a config entry."""
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    name = domain_data[CONF_NAME]
    weather_coordinator = domain_data[ENTRY_WEATHER_COORDINATOR]
    forecast_mode = domain_data[CONF_MODE]

    unique_id = f"{config_entry.unique_id}"
    service_id = config_entry.unique_id or config_entry.entry_id

    # Round Output
    output_round = domain_data[PW_ROUND]

    pw_weather = PirateWeather(
        name, unique_id, forecast_mode, weather_coordinator, output_round, service_id
    )

    async_add_entities([pw_weather], False)
    # _LOGGER.info(pw_weather.__dict__)


class PirateWeather(SingleCoordinatorWeatherEntity[WeatherUpdateCoordinator]):
    """Implementation of an Pirate Weather sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_should_poll = False
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY
        | WeatherEntityFeature.FORECAST_TWICE_DAILY
        | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(  # noqa: PLR0917
        self,
        name: str,
        unique_id,
        forecast_mode: str,
        weather_coordinator: WeatherUpdateCoordinator,
        output_round: str,
        service_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(weather_coordinator)
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, service_id)},
            manufacturer=MANUFACTURER,
            name=name,
        )
        self._weather_coordinator = weather_coordinator
        self._name = name
        self._mode = forecast_mode
        self._unique_id = unique_id
        self._ds_data = self._weather_coordinator.data
        self._ds_currently = self._weather_coordinator.data.currently()
        self._ds_hourly = self._weather_coordinator.data.hourly()
        self._ds_daily = self._weather_coordinator.data.daily()

        self.output_round = output_round

        units = WEATHER_UNITS.get(
            self._weather_coordinator.requested_units, WEATHER_UNITS["si"]
        )
        self._attr_native_temperature_unit = units["temperature"]
        self._attr_native_wind_speed_unit = units["wind_speed"]
        self._attr_native_pressure_unit = units["pressure"]
        self._attr_native_precipitation_unit = units["precipitation"]
        self._attr_native_visibility_unit = units["visibility"]

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return self._unique_id

    @property
    def available(self):
        """Return if weather data is available from Pirate Weather."""
        return (
            self._weather_coordinator.last_update_success
            and self._weather_coordinator.data is not None
        )

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    def _current_number(self, key, digits=2, scale=1):
        """Read a numeric current condition without inventing missing values."""
        return _number(
            self._weather_coordinator.data.currently().d.get(key), digits, scale
        )

    @property
    def native_temperature(self):
        """Return the temperature."""
        return self._current_number("temperature")

    @property
    def native_apparent_temperature(self):
        """Return the apparent temperature."""
        return self._current_number("apparentTemperature")

    @property
    def cloud_coverage(self):
        """Return the cloud coverage."""
        return self._current_number("cloudCover", scale=100)

    @property
    def humidity(self):
        """Return the humidity."""
        return self._current_number("humidity", scale=100)

    @property
    def native_dew_point(self):
        """Return the dew point."""
        return self._current_number("dewPoint")

    @property
    def native_wind_speed(self):
        """Return the wind speed."""
        return self._current_number("windSpeed")

    @property
    def native_wind_gust_speed(self):
        """Return the wind gust speed."""
        return self._current_number("windGust")

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        return self._current_number("windBearing", digits=None)

    @property
    def ozone(self):
        """Return the ozone."""
        return self._current_number("ozone")

    @property
    def native_pressure(self):
        """Return the pressure."""
        return self._current_number("pressure")

    @property
    def native_visibility(self):
        """Return the visibility."""
        return self._current_number("visibility")

    @property
    def condition(self):
        """Return the weather condition."""
        return MAP_CONDITION.get(
            self._weather_coordinator.data.currently().d.get("icon")
        )

    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        daily_forecast = self._weather_coordinator.data.daily().data
        if not daily_forecast:
            return None

        return [
            _map_daily_forecast(f, self._weather_coordinator.requested_units)
            for f in daily_forecast
        ]

    @callback
    def _async_forecast_twice_daily(self) -> list[Forecast] | None:
        """Return the twice daily forecast."""
        day_night_forecast = self._weather_coordinator.data.day_night().data
        if not day_night_forecast:
            _LOGGER.debug("No twice daily forecast")
            return None

        # The API returns twice-daily blocks in alternating order: day, night,
        # day, night, ... so infer daytime by index parity (even index = day).
        return [
            _map_day_night_forecast(
                f, self._weather_coordinator.requested_units, (i % 2) == 0
            )
            for i, f in enumerate(day_night_forecast)
        ]

    @callback
    def _async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast."""
        hourly_forecast = self._weather_coordinator.data.hourly().data

        if not hourly_forecast:
            return None

        return [
            _map_hourly_forecast(f, self._weather_coordinator.requested_units)
            for f in hourly_forecast
        ]
