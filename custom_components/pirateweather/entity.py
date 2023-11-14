"""Base entity for weatherkit."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, MANUFACTURER, PW_PLATFORM
from .coordinator import PirateWeatherKitDataUpdateCoordinator

from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODE,
    CONF_NAME,
)

class PirateWeatherKitEntity(Entity):
    """Base entity for all WeatherKit platforms."""

    _attr_has_entity_name = True
    _attr_name = None
    
    
    def __init__(
        self, coordinator: PirateWeatherKitDataUpdateCoordinator | None
    ) -> None:
        """Initialize the entity with device info and unique ID."""
        config_data = coordinator.config_entry.data

        latitude = config_data[CONF_LATITUDE]
        longitude = config_data[CONF_LONGITUDE]
        forecastMode = config_data[CONF_MODE]
        forecastPlatform = config_data[PW_PLATFORM]
        entityName = config_data[CONF_NAME]

        config_entry_unique_id =(
              f"pw-{latitude}-{longitude}-{forecastPlatform}-{forecastMode}-{entityName}"
            )
        
        self._attr_unique_id = config_entry_unique_id

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, config_entry_unique_id)},
            manufacturer=MANUFACTURER,
        )
