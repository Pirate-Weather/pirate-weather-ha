"""Test the Pirate Weather config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.pirateweather.const import (
    CONF_ENDPOINT,
    DEFAULT_ENDPOINT,
    DEFAULT_NAME,
    DOMAIN,
)


async def test_form(
    hass: HomeAssistant,
    mock_get_clientsession_config_flow,
    mock_api_key,
    mock_latitude,
    mock_longitude,
) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: mock_api_key,
            CONF_LATITUDE: mock_latitude,
            CONF_LONGITUDE: mock_longitude,
            CONF_NAME: DEFAULT_NAME,
            CONF_ENDPOINT: DEFAULT_ENDPOINT,
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == DEFAULT_NAME
    # Check that the required fields are present
    assert result2["data"][CONF_API_KEY] == mock_api_key
    assert result2["data"][CONF_LATITUDE] == mock_latitude
    assert result2["data"][CONF_LONGITUDE] == mock_longitude
    assert result2["data"][CONF_NAME] == DEFAULT_NAME
    assert result2["data"][CONF_ENDPOINT] == DEFAULT_ENDPOINT


async def test_form_invalid_api_key(
    hass: HomeAssistant, mock_api_key, mock_latitude, mock_longitude
) -> None:
    """Test we handle invalid API key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Mock a 403 response for invalid API key
    class AsyncContextManagerMock:
        """Mock async context manager for response."""

        def __init__(self, mock_resp):
            self.mock_resp = mock_resp

        async def __aenter__(self):
            return self.mock_resp

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    mock_resp = AsyncMock()
    mock_resp.status = 403
    mock_resp.raise_for_status = Mock()
    mock_resp.json = AsyncMock(return_value={})
    mock_session = AsyncMock()
    mock_session.get = Mock(return_value=AsyncContextManagerMock(mock_resp))

    with patch(
        "custom_components.pirateweather.config_flow.async_get_clientsession",
        return_value=mock_session,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "invalid_key",
                CONF_LATITUDE: mock_latitude,
                CONF_LONGITUDE: mock_longitude,
                CONF_NAME: DEFAULT_NAME,
                CONF_ENDPOINT: DEFAULT_ENDPOINT,
            },
        )
        await hass.async_block_till_done()

        assert result2["type"] is FlowResultType.FORM
        assert result2["errors"] == {
            "base": "Invalid API Key, Ensure that you've subscribed to API at https://pirate-weather.apiable.io/"
        }


async def test_form_duplicate(
    hass: HomeAssistant,
    mock_get_clientsession_config_flow,
    mock_api_key,
    mock_latitude,
    mock_longitude,
) -> None:
    """Test we handle duplicate entries."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: mock_api_key,
            CONF_LATITUDE: mock_latitude,
            CONF_LONGITUDE: mock_longitude,
            CONF_NAME: DEFAULT_NAME,
            CONF_ENDPOINT: DEFAULT_ENDPOINT,
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY

    # Try to create another entry with same location and settings
    result3 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"],
        {
            CONF_API_KEY: mock_api_key,
            CONF_LATITUDE: mock_latitude,
            CONF_LONGITUDE: mock_longitude,
            CONF_NAME: DEFAULT_NAME,
            CONF_ENDPOINT: DEFAULT_ENDPOINT,
        },
    )
    await hass.async_block_till_done()

    assert result4["type"] is FlowResultType.ABORT
    assert result4["reason"] == "already_configured"


async def test_options_flow(
    hass: HomeAssistant, mock_get_clientsession_config_flow, mock_config_entry
) -> None:
    """Test options flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
