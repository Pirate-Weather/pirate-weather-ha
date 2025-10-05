"""Test the Pirate Weather coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pirateweather.const import DEFAULT_ENDPOINT, DOMAIN
from custom_components.pirateweather.weather_update_coordinator import (
    WeatherUpdateCoordinator,
)


async def test_coordinator_update_success(
    hass: HomeAssistant,
    mock_get_clientsession,
    mock_api_key,
    mock_latitude,
    mock_longitude,
) -> None:
    """Test successful coordinator data update."""
    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        data={},
        unique_id="test_unique_id",
    )

    coordinator = WeatherUpdateCoordinator(
        api_key=mock_api_key,
        latitude=mock_latitude,
        longitude=mock_longitude,
        scan_interval=timedelta(seconds=300),
        language="en",
        endpoint=DEFAULT_ENDPOINT,
        units="us",
        hass=hass,
        config_entry=entry,
        models=None,
    )

    await coordinator.async_refresh()

    assert coordinator.data is not None
    assert coordinator.data.currently is not None
    assert coordinator.data.hourly is not None
    assert coordinator.data.daily is not None


async def test_coordinator_update_failure(
    hass: HomeAssistant,
    mock_api_key,
    mock_latitude,
    mock_longitude,
) -> None:
    """Test coordinator handles API errors."""
    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        data={},
        unique_id="test_unique_id",
    )

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
    # raise_for_status is a synchronous method on aiohttp responses; make it
    # a regular Mock so calling it doesn't produce an un-awaited coroutine.
    mock_resp.raise_for_status = Mock(side_effect=Exception("API Error"))
    # Provide a json coroutine that returns an empty dict so Forecast doesn't
    # receive an AsyncMock as its data. This keeps behavior consistent and
    # avoids runtime warnings if the json coroutine is awaited anywhere.
    mock_resp.json = AsyncMock(return_value={})

    mock_session = AsyncMock()
    mock_session.get = Mock(return_value=AsyncContextManagerMock(mock_resp))

    with patch(
        "custom_components.pirateweather.weather_update_coordinator.async_get_clientsession",
        return_value=mock_session,
    ):
        coordinator = WeatherUpdateCoordinator(
            api_key=mock_api_key,
            latitude=mock_latitude,
            longitude=mock_longitude,
            scan_interval=timedelta(seconds=300),
            language="en",
            endpoint=DEFAULT_ENDPOINT,
            units="us",
            hass=hass,
            config_entry=entry,
            models=None,
        )

        # Coordinator should handle error gracefully
        await coordinator.async_refresh()

        # Check that last update failed
        assert coordinator.last_update_success is False
        assert coordinator.last_exception is not None


async def test_coordinator_with_models_exclusion(
    hass: HomeAssistant,
    mock_get_clientsession,
    mock_api_key,
    mock_latitude,
    mock_longitude,
) -> None:
    """Test coordinator with model exclusions."""
    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        data={},
        unique_id="test_unique_id",
    )

    coordinator = WeatherUpdateCoordinator(
        api_key=mock_api_key,
        latitude=mock_latitude,
        longitude=mock_longitude,
        scan_interval=timedelta(seconds=300),
        language="en",
        endpoint=DEFAULT_ENDPOINT,
        units="us",
        hass=hass,
        config_entry=entry,
        models="gfs,nam",
    )

    await coordinator.async_refresh()

    assert coordinator.data is not None
    # Verify the API was called with exclude parameter
    mock_get_clientsession.return_value.get.assert_called()
    call_args = mock_get_clientsession.return_value.get.call_args
    assert "exclude=" in call_args[0][0]
