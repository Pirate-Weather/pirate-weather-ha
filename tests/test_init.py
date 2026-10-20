"""Test the Pirate Weather integration initialization."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_KEY, CONF_MONITORED_CONDITIONS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from custom_components.pirateweather.const import DEFAULT_NAME, DOMAIN, PW_PLATFORM


async def test_setup_entry(
    hass: HomeAssistant,
    mock_get_clientsession,
    mock_config_entry,
) -> None:
    """Test successful setup of a config entry."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]

    device_registry = dr.async_get(hass)
    service_device = device_registry.async_get_device_by_identifier(
        (DOMAIN, "test_unique_id"), mock_config_entry.entry_id
    )
    assert service_device is not None
    assert service_device.entry_type is DeviceEntryType.SERVICE
    assert service_device.manufacturer == "PirateWeather"


async def test_unload_entry(
    hass: HomeAssistant,
    mock_get_clientsession,
    mock_config_entry,
) -> None:
    """Test successful unload of a config entry."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})


@pytest.mark.parametrize(
    ("legacy_name", "title", "expected_name"),
    [
        (None, "", DEFAULT_NAME),
        (None, "Home forecast", "Home forecast"),
        ("Ignored legacy name", "Home forecast", "Home forecast"),
    ],
)
async def test_setup_uses_entry_title(
    hass: HomeAssistant,
    mock_get_clientsession,
    mock_config_entry,
    *,
    legacy_name,
    title,
    expected_name,
) -> None:
    """Stored names are ignored and both platforms keep their entity IDs on reload."""
    mock_config_entry.add_to_hass(hass)
    data = {
        key: value for key, value in mock_config_entry.data.items() if key != CONF_NAME
    }
    if legacy_name is not None:
        data[CONF_NAME] = legacy_name
    data[PW_PLATFORM] = ["Sensor", "Weather"]
    data[CONF_MONITORED_CONDITIONS] = ["temperature"]
    hass.config_entries.async_update_entry(
        mock_config_entry,
        data=data,
        title=title,
        options={CONF_NAME: "Ignored legacy options name"},
    )
    registry = async_get_entity_registry(hass)
    for platform, unique_id, object_id in (
        ("weather", "test_unique_id", "legacy_forecast"),
        ("sensor", "test_unique_id-sensor-temperature", "legacy_temperature"),
    ):
        registry.async_get_or_create(
            platform,
            DOMAIN,
            unique_id,
            suggested_object_id=object_id,
            config_entry=mock_config_entry,
        )
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.data[DOMAIN][mock_config_entry.entry_id][CONF_NAME] == expected_name
    entities_before = {
        entity.unique_id: entity.entity_id
        for entity in registry.entities.values()
        if entity.config_entry_id == mock_config_entry.entry_id
    }
    assert len(entities_before) == 2
    assert set(entities_before.values()) == {
        "weather.legacy_forecast",
        "sensor.legacy_temperature",
    }
    assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entities_after = {
        entity.unique_id: entity.entity_id
        for entity in registry.entities.values()
        if entity.config_entry_id == mock_config_entry.entry_id
    }
    assert entities_after == entities_before
    assert mock_config_entry.unique_id == "test_unique_id"


async def test_options_api_key_reload(
    hass: HomeAssistant,
    mock_get_clientsession,
    mock_get_clientsession_config_flow,
    mock_aiohttp_session,
    mock_config_entry,
) -> None:
    """Changing the key reloads the integration and uses it for weather requests."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    mock_aiohttp_session.get.reset_mock()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**result["data_schema"]({}), CONF_API_KEY: "replacement_key"},
    )
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert (
        hass.data[DOMAIN][mock_config_entry.entry_id][CONF_API_KEY] == "replacement_key"
    )
    # One validation request and one forecast request during the reload.
    assert mock_aiohttp_session.get.call_count == 2
    for request in mock_aiohttp_session.get.call_args_list:
        assert "/forecast/replacement_key/" in request.args[0]


async def test_setup_entry_with_coordinator_error(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test setup fails when coordinator cannot fetch data."""

    # Mock a failed API response
    class AsyncContextManagerMock:
        """Mock async context manager for response."""

        def __init__(self, mock_resp):
            self.mock_resp = mock_resp

        async def __aenter__(self):
            return self.mock_resp

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    mock_resp = AsyncMock()
    mock_resp.status = 500
    # Use a synchronous Mock for raise_for_status so it raises immediately when called
    mock_resp.raise_for_status = Mock(side_effect=ClientError("API Error"))
    # Ensure resp.json() returns a plain dict (not a coroutine) for Forecast parsing
    mock_resp.json = AsyncMock(return_value={})

    mock_session = AsyncMock()
    mock_session.get = Mock(return_value=AsyncContextManagerMock(mock_resp))

    with patch(
        "custom_components.pirateweather.weather_update_coordinator.async_get_clientsession",
        return_value=mock_session,
    ):
        mock_config_entry.add_to_hass(hass)

        # Setup should fail
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
