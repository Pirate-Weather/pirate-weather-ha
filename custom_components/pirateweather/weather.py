"""Support for the Pirate Weather (PW) service."""
from __future__ import annotations

from datetime import timedelta
import logging

from requests.exceptions import ConnectionError as ConnectError, HTTPError, Timeout
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
from homeassistant.util.dt import utc_from_timestamp
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, callback


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
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_NATIVE_PRESSURE,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_WIND_SPEED,    
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    PLATFORM_SCHEMA,
    WeatherEntity,
    Forecast,
    WeatherEntityFeature,
    SingleCoordinatorWeatherEntity,
)


from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODE,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    LENGTH_MILLIMETERS,
    PRESSURE_MBAR,
    SPEED_METERS_PER_SECOND,
    PRESSURE_HPA,
    PRESSURE_INHG,
    LENGTH_KILOMETERS,
    LENGTH_MILLIMETERS,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,    
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfLength,
)

from .const import (
    CONF_LANGUAGE,
    CONFIG_FLOW_VERSION,
    DEFAULT_FORECAST_MODE,
    DEFAULT_LANGUAGE,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FORECAST_MODES,
    LANGUAGES,
    CONF_UNITS,
    DEFAULT_UNITS,
    ENTRY_NAME,
    ENTRY_WEATHER_COORDINATOR,
    FORECAST_MODES,
    PLATFORMS,
    UPDATE_LISTENER,   
    MANUFACTURER,    
    FORECASTS_HOURLY,
    FORECASTS_DAILY,
    PW_PLATFORMS,
    PW_PLATFORM,
    PW_PREVPLATFORM,
    PW_ROUND,
    ATTR_FORECAST_CLOUD_COVERAGE,
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_NATIVE_VISIBILITY,
)


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
        vol.Optional(CONF_UNITS): vol.In(["auto", "si", "us", "ca", "uk", "uk2"]),
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
    "tornado": None,
}

CONF_UNITS = "units"

DEFAULT_NAME = "Pirate Weather"

from .weather_update_coordinator import WeatherUpdateCoordinator

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
        DOMAIN, context={"source": SOURCE_IMPORT}, data = config_entry
      )
    )


def _map_daily_forecast(forecast) -> Forecast:
    return {
        "datetime": utc_from_timestamp(forecast.d.get("time")).isoformat(),
        "condition": MAP_CONDITION.get(forecast.d.get("icon")),
        "native_temperature": forecast.d.get("temperatureHigh"),
        "native_templow": forecast.d.get("temperatureLow"),
        "native_precipitation": forecast.d.get("precipAccumulation")*10,
        "precipitation_probability":  round(forecast.d.get("precipProbability")*100, 0),
        "humidity": round(forecast.d.get("humidity")*100, 2),
        "cloud_coverage":  round(forecast.d.get("cloudCover")*100, 0),
        "native_wind_speed": round(forecast.d.get("windSpeed"), 2),
        "wind_bearing": round(forecast.d.get("windBearing"), 0),
    }

                    
def _map_hourly_forecast(forecast: dict[str, Any]) -> Forecast:
    return {
        "datetime":  utc_from_timestamp(forecast.d.get("time")).isoformat(),
        "condition":  MAP_CONDITION.get(forecast.d.get("icon")),
        "native_temperature": forecast.d.get("temperature"),
        "native_apparent_temperature": forecast.d.get("apparentTemperature"),
        "native_dew_point": forecast.d.get("dewPoint"),
        "native_pressure": forecast.d.get("pressure"),
        "native_wind_speed":round(forecast.d.get("windSpeed"), 2),
        "wind_bearing": round(forecast.d.get("windBearing"), 0),   
        "humidity": round(forecast.d.get("humidity")*100, 2),
        "native_precipitation": round(forecast.d.get("precipIntensity"), 2),
        "precipitation_probability":round(forecast.d.get("precipProbability")*100, 0),
        "cloud_coverage":  round(forecast.d.get("cloudCover")*100, 0), 
        "uv_index":  round(forecast.d.get("uvIndex"), 2), 
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
    api_key = domain_data[CONF_API_KEY]
    latitude = domain_data[CONF_LATITUDE]
    longitude = domain_data[CONF_LONGITUDE]
    #units = domain_data[CONF_UNITS]
    units = "si"
    forecast_mode = domain_data[CONF_MODE]
    
    unique_id = f"{config_entry.unique_id}"
    
    # Round Output
    outputRound = domain_data[PW_ROUND]     
     
    pw_weather = PirateWeather(name, unique_id, forecast_mode, weather_coordinator, outputRound)

    async_add_entities([pw_weather], False)
    #_LOGGER.info(pw_weather.__dict__)
    

class PirateWeather(SingleCoordinatorWeatherEntity[WeatherUpdateCoordinator]):
    """Implementation of an PirateWeather sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_should_poll = False
    
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_native_pressure_unit = UnitOfPressure.MBAR
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_visibility_unit = UnitOfLength.KILOMETERS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    
    def __init__(
        self,
        name: str,
        unique_id,
        forecast_mode: str,
        weather_coordinator: WeatherUpdateCoordinator,
        outputRound: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(weather_coordinator)
        self._attr_name = name
        #self._attr_device_info = DeviceInfo(
        #    entry_type=DeviceEntryType.SERVICE,
        #    identifiers={(DOMAIN, unique_id)},
        #    manufacturer=MANUFACTURER,
        #    name=DEFAULT_NAME,
        #)
        self._weather_coordinator = weather_coordinator
        self._name = name
        self._mode = forecast_mode
        self._unique_id = unique_id 
        self._ds_data = self._weather_coordinator.data
        self._ds_currently = self._weather_coordinator.data.currently()
        self._ds_hourly = self._weather_coordinator.data.hourly()
        self._ds_daily = self._weather_coordinator.data.daily()
        
        self.outputRound = outputRound

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return self._unique_id
        
    @property
    def supported_features(self) -> WeatherEntityFeature:
        """Determine supported features based on available data sets reported by WeatherKit."""
        features = WeatherEntityFeature(0)

        features |= WeatherEntityFeature.FORECAST_DAILY
        features |= WeatherEntityFeature.FORECAST_HOURLY
        return features        
        
    @property
    def available(self):
        """Return if weather data is available from PirateWeather."""
        return self._weather_coordinator.data is not None

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def native_temperature(self):
        """Return the temperature."""
        temperature = self._weather_coordinator.data.currently().d.get("temperature")
        
        if self.outputRound=="Yes":
          return round(temperature, 0)+0
        else:
          return round(temperature, 2)
                
    @property
    def humidity(self):
        """Return the humidity."""
        humidity = self._weather_coordinator.data.currently().d.get("humidity") * 100.0

        if self.outputRound=="Yes":
          return round(humidity, 0)+0
        else:
          return round(humidity, 2)
          
          
    @property
    def native_wind_speed(self):
        """Return the wind speed."""
        windspeed = self._weather_coordinator.data.currently().d.get("windSpeed")

        if self.outputRound=="Yes":
          return round(windspeed, 0)+0
        else:
          return round(windspeed, 2)
          
    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        return self._weather_coordinator.data.currently().d.get("windBearing")

    @property
    def ozone(self):
        """Return the ozone level."""
        ozone = self._weather_coordinator.data.currently().d.get("ozone")
        
        if self.outputRound=="Yes":
          return round(ozone, 0)+0
        else:
          return round(ozone, 2)
          
    @property
    def native_pressure(self):
        """Return the pressure."""
        pressure = self._weather_coordinator.data.currently().d.get("pressure")
        
        if self.outputRound=="Yes":
          return round(pressure, 0)+0
        else:
          return round(pressure, 2)

        
    @property
    def native_visibility(self):
        """Return the visibility."""
        visibility = self._weather_coordinator.data.currently().d.get("visibility")
        
        if self.outputRound=="Yes":
          return round(visibility, 0)+0
        else:
          return round(visibility, 2)        

    @property
    def condition(self):
        """Return the weather condition."""

        return MAP_CONDITION.get(self._weather_coordinator.data.currently().d.get("icon"))


    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""        
        daily_forecast = self._weather_coordinator.data.daily().data
        if not daily_forecast:
            return None

        return [_map_daily_forecast(f) for f in daily_forecast]

    @callback
    def _async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast."""       
        hourly_forecast = self._weather_coordinator.data.hourly().data
        
        if not hourly_forecast:
            return None

        return [_map_hourly_forecast(f) for f in hourly_forecast]
        
    
    async def async_update(self) -> None:
        """Get the latest data from PW and updates the states."""
        await self._weather_coordinator.async_request_refresh()   
         
#    async def update(self):
#        """Get the latest data from Dark Sky."""
#        await self._dark_sky.update()
#
#        self._ds_data = self._dark_sky.data
#        currently = self._dark_sky.currently
#        self._ds_currently = currently.d if currently else {}
#        self._ds_hourly = self._dark_sky.hourly
#        self._ds_daily = self._dark_sky.daily
        
    async def async_added_to_hass(self) -> None:
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self._weather_coordinator.async_add_listener(self.async_write_ha_state)
        )
