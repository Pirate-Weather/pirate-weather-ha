"""Fixtures for Pirate Weather tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pirateweather.const import (
    CONF_ENDPOINT,
    CONF_LANGUAGE,
    CONF_MODELS,
    CONF_UNITS,
    DEFAULT_ENDPOINT,
    DEFAULT_LANGUAGE,
    DEFAULT_NAME,
    DEFAULT_UNITS,
    DOMAIN,
    PW_PLATFORM,
    PW_ROUND,
)

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return


@pytest.fixture
def mock_api_key():
    """Return a mock API key."""
    return "test_api_key_123456"


@pytest.fixture
def mock_latitude():
    """Return a mock latitude."""
    return 37.8267


@pytest.fixture
def mock_longitude():
    """Return a mock longitude."""
    return -122.4233


@pytest.fixture
def mock_config_entry_data(mock_api_key, mock_latitude, mock_longitude):
    """Return mock config entry data."""
    return {
        CONF_API_KEY: mock_api_key,
        CONF_LATITUDE: mock_latitude,
        CONF_LONGITUDE: mock_longitude,
        CONF_NAME: DEFAULT_NAME,
        CONF_ENDPOINT: DEFAULT_ENDPOINT,
        CONF_LANGUAGE: DEFAULT_LANGUAGE,
        CONF_UNITS: DEFAULT_UNITS,
        CONF_MONITORED_CONDITIONS: [],
        CONF_SCAN_INTERVAL: 1200,
        PW_PLATFORM: ["Weather"],
        PW_ROUND: "No",
        CONF_MODELS: None,
    }


@pytest.fixture
def mock_pirate_weather_response():
    """Load and return mock Pirate Weather API response."""
    fixture_path = Path(__file__).parent / "fixtures" / "pirate_weather_response.json"
    with fixture_path.open() as f:
        return json.load(f)


@pytest.fixture
def mock_aiohttp_session(mock_pirate_weather_response):
    """Mock aiohttp client session."""

    class AsyncContextManagerMock:
        """Mock async context manager for response."""

        def __init__(self, mock_resp):
            self.mock_resp = mock_resp

        async def __aenter__(self):
            return self.mock_resp

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=mock_pirate_weather_response)
    mock_resp.headers = {"X-Forecast-API-Calls": "1", "X-Response-Time": "100"}
    mock_resp.raise_for_status = Mock()

    mock_session = AsyncMock()
    mock_session.get = Mock(return_value=AsyncContextManagerMock(mock_resp))

    return mock_session


@pytest.fixture
def mock_get_clientsession(mock_aiohttp_session):
    """Mock async_get_clientsession."""
    with patch(
        "custom_components.pirateweather.weather_update_coordinator.async_get_clientsession",
        return_value=mock_aiohttp_session,
    ) as mock:
        yield mock


@pytest.fixture
def mock_get_clientsession_config_flow(mock_aiohttp_session):
    """Mock async_get_clientsession for config flow."""
    with patch(
        "custom_components.pirateweather.config_flow.async_get_clientsession",
        return_value=mock_aiohttp_session,
    ) as mock:
        yield mock


@pytest.fixture
async def mock_config_entry(mock_config_entry_data):
    """Return a mock config entry."""
    return MockConfigEntry(
        version=2,
        domain=DOMAIN,
        data=mock_config_entry_data,
        unique_id="test_unique_id",
    )
