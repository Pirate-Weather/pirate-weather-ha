"""Test the Pirate Weather config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import ClientError
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
    assert (
        result["data_schema"]({})[CONF_API_KEY] == mock_config_entry.data[CONF_API_KEY]
    )


async def test_options_flow_change_api_key(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Save a validated replacement and show it when options are reopened."""
    mock_config_entry.add_to_hass(hass)
    original_data = dict(mock_config_entry.data)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    user_input = {**result["data_schema"]({}), CONF_API_KEY: "  replacement_key  "}

    with patch(
        "custom_components.pirateweather.config_flow._is_pw_api_online",
        return_value=200,
    ) as validate:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input=user_input
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_API_KEY] == "replacement_key"
    assert mock_config_entry.data == original_data
    validate.assert_awaited_once_with(
        hass,
        "replacement_key",
        user_input[CONF_LATITUDE],
        user_input[CONF_LONGITUDE],
        user_input[CONF_ENDPOINT],
    )
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["data_schema"]({})[CONF_API_KEY] == "replacement_key"


@pytest.mark.parametrize(
    ("api_key", "status", "exception", "errors"),
    [
        ("bad_key", 401, None, {CONF_API_KEY: "invalid_api_key"}),
        ("bad_key", 403, None, {CONF_API_KEY: "invalid_api_key"}),
        ("   ", 200, None, {CONF_API_KEY: "invalid_api_key"}),
        ("new_key", 429, None, {"base": "cannot_connect"}),
        ("new_key", 500, None, {"base": "cannot_connect"}),
        ("new_key", 200, ClientError(), {"base": "cannot_connect"}),
        ("new_key", 200, TimeoutError(), {"base": "cannot_connect"}),
    ],
)
async def test_options_flow_rejects_invalid_api_key(
    hass: HomeAssistant, mock_config_entry, *, api_key, status, exception, errors
) -> None:
    """Failed validation preserves the saved key and permits a corrected submission."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={CONF_API_KEY: "working_key"}
    )
    original_data = dict(mock_config_entry.data)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    user_input = {**result["data_schema"]({}), CONF_API_KEY: api_key}

    with patch(
        "custom_components.pirateweather.config_flow._is_pw_api_online",
        return_value=status,
        side_effect=exception,
    ) as validate:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input=user_input
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors
    assert mock_config_entry.options[CONF_API_KEY] == "working_key"
    assert mock_config_entry.data == original_data
    if not api_key.strip():
        validate.assert_not_awaited()

    with patch(
        "custom_components.pirateweather.config_flow._is_pw_api_online",
        return_value=200,
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={**user_input, CONF_API_KEY: "corrected_key"},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_API_KEY] == "corrected_key"
