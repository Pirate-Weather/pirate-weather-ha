"""Test the Pirate Weather integration initialization."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntryType

from custom_components.pirateweather.const import DOMAIN


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
