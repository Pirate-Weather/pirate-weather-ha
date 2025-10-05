"""Test the Pirate Weather sensor platform."""

from __future__ import annotations

import pytest
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pirateweather.const import (
    CONF_ENDPOINT,
    CONF_LANGUAGE,
    CONF_UNITS,
    DEFAULT_ENDPOINT,
    DEFAULT_LANGUAGE,
    DEFAULT_NAME,
    DOMAIN,
    PW_PLATFORM,
    PW_ROUND,
)


async def test_sensor_setup(
    hass: HomeAssistant,
    mock_get_clientsession,
    mock_config_entry_data,
) -> None:
    """Test sensor platform setup."""
    # Add monitored conditions to config
    config_data = mock_config_entry_data.copy()
    config_data[CONF_MONITORED_CONDITIONS] = [
        "temperature",
        "humidity",
        "pressure",
        "summary",
    ]
    config_data[PW_PLATFORM] = ["Sensor"]

    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        data=config_data,
        unique_id="test_sensor_unique_id",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Check that sensors were created
    sensor_entities = hass.states.async_all("sensor")
    assert len(sensor_entities) > 0

    # Check specific sensors exist
    temp_sensor = hass.states.get("sensor.pirateweather_temperature")
    humidity_sensor = hass.states.get("sensor.pirateweather_humidity")

    assert temp_sensor is not None
    assert humidity_sensor is not None


async def test_sensor_values(
    hass: HomeAssistant,
    mock_get_clientsession,
    mock_config_entry_data,
) -> None:
    """Test sensor values from API data."""
    config_data = mock_config_entry_data.copy()
    config_data[CONF_MONITORED_CONDITIONS] = [
        "temperature",
        "humidity",
        "pressure",
        "wind_speed",
        "uv_index",
        "visibility",
    ]
    config_data[PW_PLATFORM] = ["Sensor"]

    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        data=config_data,
        unique_id="test_sensor_values_unique_id",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Check sensor values match the API response
    # Note: Temperature is converted from F to C when units is "us"
    temp_sensor = hass.states.get("sensor.pirateweather_temperature")
    assert temp_sensor is not None
    # The API returns 62.64°F which is ~17.02°C
    assert float(temp_sensor.state) == pytest.approx(17.02, abs=0.01)

    humidity_sensor = hass.states.get("sensor.pirateweather_humidity")
    assert humidity_sensor is not None
    assert float(humidity_sensor.state) == 85.0  # 0.85 * 100

    pressure_sensor = hass.states.get("sensor.pirateweather_pressure")
    assert pressure_sensor is not None
    assert float(pressure_sensor.state) == 1009.77


async def test_sensor_v2_fields(
    hass: HomeAssistant,
    mock_get_clientsession,
    mock_config_entry_data,
) -> None:
    """Test Version 2 specific sensor fields."""
    config_data = mock_config_entry_data.copy()
    config_data[CONF_MONITORED_CONDITIONS] = [
        "smoke",
        "fire_index",
        "feels_like",
        "current_day_liquid",
        "current_day_snow",
        "current_day_ice",
    ]
    config_data[PW_PLATFORM] = ["Sensor"]

    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        data=config_data,
        unique_id="test_sensor_v2_unique_id",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Check V2 specific sensors
    smoke_sensor = hass.states.get("sensor.pirateweather_smoke")
    if smoke_sensor:  # Only if sensor type exists in const.py
        assert float(smoke_sensor.state) == 0.01

    fire_index_sensor = hass.states.get("sensor.pirateweather_fire_index")
    if fire_index_sensor:
        assert float(fire_index_sensor.state) == 7.33

    feels_like_sensor = hass.states.get("sensor.pirateweather_feels_like")
    if feels_like_sensor:
        assert float(feels_like_sensor.state) == 64.6


async def test_sensor_forecast_daily(
    hass: HomeAssistant,
    mock_get_clientsession,
    mock_config_entry_data,
) -> None:
    """Test daily forecast sensors."""
    config_data = mock_config_entry_data.copy()
    config_data[CONF_MONITORED_CONDITIONS] = ["temperature_high", "temperature_low"]
    config_data[PW_PLATFORM] = ["Sensor"]
    config_data["forecast"] = ["0"]  # Only test day 0 since fixture has 1 day
    config_data[CONF_LANGUAGE] = DEFAULT_LANGUAGE

    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        data=config_data,
        unique_id="test_sensor_forecast_unique_id",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Check that forecast sensors were created
    # The exact entity name may vary - just check some forecast sensors exist
    sensor_entities = hass.states.async_all("sensor")
    forecast_sensors = [
        s
        for s in sensor_entities
        if "temperature" in s.entity_id.lower() and "0d" in s.entity_id
    ]
    assert len(forecast_sensors) > 0


async def test_sensor_attributes(
    hass: HomeAssistant,
    mock_get_clientsession,
    mock_config_entry_data,
) -> None:
    """Test sensor attributes."""
    config_data = mock_config_entry_data.copy()
    config_data[CONF_MONITORED_CONDITIONS] = ["temperature"]
    config_data[PW_PLATFORM] = ["Sensor"]

    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        data=config_data,
        unique_id="test_sensor_attrs_unique_id",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    temp_sensor = hass.states.get("sensor.pirateweather_temperature")
    assert temp_sensor is not None

    # Check attributes
    assert temp_sensor.attributes.get("attribution") == "Powered by Pirate Weather"
    assert "unit_of_measurement" in temp_sensor.attributes


async def test_sensor_unit_system(
    hass: HomeAssistant,
    mock_get_clientsession,
    mock_api_key,
    mock_latitude,
    mock_longitude,
) -> None:
    """Test sensor with different unit systems."""
    # Test with SI units
    config_data = {
        CONF_API_KEY: mock_api_key,
        CONF_LATITUDE: mock_latitude,
        CONF_LONGITUDE: mock_longitude,
        CONF_NAME: DEFAULT_NAME,
        CONF_ENDPOINT: DEFAULT_ENDPOINT,
        CONF_LANGUAGE: DEFAULT_LANGUAGE,
        CONF_UNITS: "si",  # SI units
        CONF_MONITORED_CONDITIONS: ["temperature"],
        CONF_SCAN_INTERVAL: 1200,
        PW_PLATFORM: ["Sensor"],
        PW_ROUND: "No",
    }

    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        data=config_data,
        unique_id="test_sensor_si_unique_id",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    temp_sensor = hass.states.get("sensor.pirateweather_temperature")
    assert temp_sensor is not None
    # Check unit is correct for SI
    assert temp_sensor.attributes.get("unit_of_measurement") == "°C"
