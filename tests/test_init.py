"""Test the Pirate Weather integration initialization."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

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
