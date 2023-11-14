"""WeatherKit sensors."""


from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolumetricFlux
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_CURRENT_WEATHER, DOMAIN
from .coordinator import PirateWeatherKitDataUpdateCoordinator
from .entity import PirateWeatherKitEntity

SENSORS = (
    SensorEntityDescription(
        key="precipitationIntensity",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
    ),
    SensorEntityDescription(
        key="pressureTrend",
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:gauge",
        options=["rising", "falling", "steady"],
        translation_key="pressure_trend",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensor entities from a config_entry."""
    coordinator: PirateWeatherKitDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

 
    forecast_days = _get_config_value(coordinator.config_entry, CONF_FORECAST)
    forecast_hours = _get_config_value(coordinator.config_entry, CONF_HOURLY_FORECAST)
    
    
   # Set sensors to be created
    if type(forecast_days) == str:
      # If empty, set to none
      if forecast_days  == "" or forecast_days  == "None":
        forecast_days = None
      else:
        if forecast_days[0] == '[':
          forecast_days = forecast_days[1:-1].split(",")
        else:    
          forecast_days = forecast_days.split(",")
        forecast_days = [int(i) for i in forecast_days]
        
    if type(forecast_hours) == str:
    # If empty, set to none
      if forecast_hours == "" or forecast_hours  == "None":
        forecast_hours = None
      else:
        if forecast_hours[0] == '[':
          forecast_hours = forecast_hours[1:-1].split(",")
        else:    
          forecast_hours = forecast_hours.split(",")
        forecast_hours = [int(i) for i in forecast_hours]

    async_add_entities(
        PirateWeatherKitSensor(coordinator, description) for description in SENSORS
    )


class PirateWeatherKitSensor(
    CoordinatorEntity[PirateWeatherKitDataUpdateCoordinator], PirateWeatherKitEntity, SensorEntity
):
    """WeatherKit sensor entity."""

    def __init__(
        self,
        coordinator: PirateWeatherKitDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        PirateWeatherKitEntity.__init__(
            self, coordinator, unique_id_suffix=entity_description.key
        )
        self.entity_description = entity_description

    @property
    def native_value(self) -> StateType:
        """Return native value from coordinator current weather."""
        return self.coordinator.data[ATTR_CURRENT_WEATHER][self.entity_description.key]


def _get_config_value(config_entry: ConfigEntry, key: str) -> Any:
    if config_entry.options:
        return config_entry.options[key]
    return config_entry.data[key]