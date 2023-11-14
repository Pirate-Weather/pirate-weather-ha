"""Weather entity for Apple WeatherKit integration."""

from typing import Any, cast

from apple_weatherkit import DataSetType

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    Forecast,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature, 
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTRIBUTION,
    DOMAIN,
    LOGGER,
    PW_ROUND,
)
from .coordinator import PirateWeatherKitDataUpdateCoordinator
from .entity import PirateWeatherKitEntity

from homeassistant.util.dt import utc_from_timestamp

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a weather entity from a config_entry."""
    coordinator: PirateWeatherKitDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    domain_data = coordinator.config_entry.data
    
    # Round Output
    outputRound = domain_data[PW_ROUND] 
    
    

    async_add_entities([PirateWeatherKitWeather(coordinator, outputRound)])


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
    "tornado": None,
}

def _map_daily_forecast(forecast) -> Forecast:
    return {
        "datetime": utc_from_timestamp(forecast.time).isoformat(),
        "condition": MAP_CONDITION.get(forecast.icon),
        "native_temperature": forecast.temperature_high,
        "native_templow": forecast.temperature_low,
        "native_precipitation": forecast.precipAccumulation*10,
        "precipitation_probability":  forecast.uv_index  
    }


def _map_hourly_forecast(forecast: dict[str, Any]) -> Forecast:
    return {
        "datetime": utc_from_timestamp(forecast.time).isoformat(),
        "condition": MAP_CONDITION.get(forecast.icon),
        "native_temperature": forecast.temperature,
        "native_apparent_temperature": forecast.apparent_temperature,
        "native_dew_point": forecast.dew_point,
        "native_pressure": forecast.pressure,
        "native_wind_gust_speed": round(forecast.wind_gust, 2),
        "native_wind_speed": round(forecast.wind_speed, 2),
        "wind_bearing": round(forecast.wind_bearing, 0), 
        "humidity": round(forecast.humidity*100, 2),
        "native_precipitation": round(forecast.precip_intensity, 2),
        "precipitation_probability": round(forecast.precip_probability*100, 0),
        "cloud_coverage": forecast.cloud_cover * 100,
        "uv_index": forecast.uv_index,
    }


class PirateWeatherKitWeather(
    SingleCoordinatorWeatherEntity[PirateWeatherKitDataUpdateCoordinator], PirateWeatherKitEntity
):
    """Weather entity for Pirate Weather integration."""

    _attr_attribution = ATTRIBUTION

    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.MBAR
    _attr_native_visibility_unit = UnitOfLength.KILOMETERS
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_precipitation_unit = UnitOfLength.MILLIMETERS

    def __init__(
        self,
        coordinator: PirateWeatherKitDataUpdateCoordinator,
        outputRound: str,
    ) -> None:
        """Initialize the platform with a coordinator."""
        super().__init__(coordinator)
        PirateWeatherKitEntity.__init__(self, coordinator)
        
        
    @property
    def supported_features(self) -> WeatherEntityFeature:
        """Determine supported features based on available data sets reported by WeatherKit."""
        features = WeatherEntityFeature(0)

        features |= WeatherEntityFeature.FORECAST_DAILY
        features |= WeatherEntityFeature.FORECAST_HOURLY
        return features

    @property
    def data(self) -> dict[str, Any]:
        """Return coordinator data."""
        LOGGER.warning(self.coordinator.data)
        
        return self.coordinator.data

    @property
    def current_weather(self) -> dict[str, Any]:
        """Return current weather data."""
        return self.data.currently

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        return MAP_CONDITION.get(self.current_weather.icon)

    @property
    def native_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.current_weather.temperature

    @property
    def native_apparent_temperature(self) -> float | None:
        """Return the current apparent_temperature."""
        return self.current_weather.apparent_temperature

    @property
    def native_dew_point(self) -> float | None:
        """Return the current dew_point."""
        return self.current_weather.dew_point

    @property
    def native_pressure(self) -> float | None:
        """Return the current pressure."""
        return self.current_weather.pressure

    @property
    def humidity(self) -> float | None:
        """Return the current humidity."""
        return cast(float, self.current_weather.humidity) * 100

    @property
    def cloud_coverage(self) -> float | None:
        """Return the current cloud_coverage."""
        return cast(float, self.current_weather.cloud_cover) * 100

    @property
    def uv_index(self) -> float | None:
        """Return the current uv_index."""
        return self.current_weather.uv_index

    @property
    def native_visibility(self) -> float | None:
        """Return the current visibility."""
        return cast(float, self.current_weather.visibility) / 1000

    @property
    def native_wind_gust_speed(self) -> float | None:
        """Return the current wind_gust_speed."""
        return self.current_weather.wind_gust

    @property
    def native_wind_speed(self) -> float | None:
        """Return the current wind_speed."""
        return self.current_weather.wind_speed

    @property
    def wind_bearing(self) -> float | None:
        """Return the current wind_bearing."""
        return self.current_weather.wind_bearing

    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""        
        daily_forecast = self.data.daily
        if not daily_forecast:
            return None

        return [_map_daily_forecast(f) for f in daily_forecast]

    @callback
    def _async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast."""       
        hourly_forecast = self.data.hourly
        
        if not hourly_forecast:
            return None

        return [_map_hourly_forecast(f) for f in hourly_forecast]
