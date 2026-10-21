"""Test advanced form sections without changing stored integration settings."""

from unittest.mock import patch

import probatio
import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_validation as cv

from custom_components.pirateweather.const import (
    CONF_ENDPOINT,
    CONF_MODELS,
    CONF_UNITS,
    DOMAIN,
    PW_ROUND,
)

ADVANCED_SETTINGS = {
    CONF_MODELS: "hrrr,nbm",
    PW_ROUND: "Yes",
    CONF_ENDPOINT: "https://weather.example.test",
    CONF_UNITS: "si",
}


@pytest.mark.parametrize("flow_type", ["setup", "options"])
async def test_advanced_section(hass, mock_config_entry, flow_type):
    """Only the four requested fields are grouped and collapsed by default."""
    if flow_type == "setup":
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    else:
        mock_config_entry.add_to_hass(hass)
        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )
    fields = probatio.to_field_list(
        result["data_schema"], custom_serializer=cv.custom_serializer
    )
    advanced = next(field for field in fields if field["name"] == "advanced")
    assert advanced["type"] == "expandable"
    assert advanced["expanded"] is False
    assert {field["name"] for field in advanced["schema"]} == ADVANCED_SETTINGS.keys()
    assert not ADVANCED_SETTINGS.keys() & {field["name"] for field in fields}


@pytest.mark.parametrize("source", ["data", "options"])
async def test_closed_advanced_section_preserves_settings(
    hass, mock_config_entry, *, source
):
    """Saving a closed section retains nondefault settings from data or options."""
    mock_config_entry.add_to_hass(hass)
    if source == "data":
        hass.config_entries.async_update_entry(
            mock_config_entry, data={**mock_config_entry.data, **ADVANCED_SETTINGS}
        )
    else:
        hass.config_entries.async_update_entry(
            mock_config_entry, options=ADVANCED_SETTINGS
        )
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    defaults = result["data_schema"]({"advanced": {}})
    assert defaults["advanced"] == ADVANCED_SETTINGS
    with patch(
        "custom_components.pirateweather.config_flow._is_pw_api_online",
        return_value=200,
    ) as validate:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"advanced": {}}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    for key, value in ADVANCED_SETTINGS.items():
        assert mock_config_entry.options[key] == value
    assert "advanced" not in mock_config_entry.options
    assert validate.await_args.args[-1] == ADVANCED_SETTINGS[CONF_ENDPOINT]


@pytest.mark.parametrize("flow_type", ["setup", "options"])
async def test_edit_advanced_settings(hass, mock_config_entry, flow_type):
    """Nested form input is validated with the chosen endpoint and saved flat."""
    if flow_type == "setup":
        manager = hass.config_entries.flow
        result = await manager.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    else:
        mock_config_entry.add_to_hass(hass)
        manager = hass.config_entries.options
        result = await manager.async_init(mock_config_entry.entry_id)
    with patch(
        "custom_components.pirateweather.config_flow._is_pw_api_online",
        return_value=200,
    ) as validate:
        result = await manager.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: mock_config_entry.data[CONF_API_KEY],
                "advanced": ADVANCED_SETTINGS,
            },
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "advanced" not in result["data"]
    for key, value in ADVANCED_SETTINGS.items():
        assert result["data"][key] == value
    assert validate.await_args.args[-1] == ADVANCED_SETTINGS[CONF_ENDPOINT]


async def test_validation_error_retains_advanced_settings(hass, mock_config_entry):
    """An API key error keeps edits to the nested advanced fields."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_API_KEY: " ", "advanced": ADVANCED_SETTINGS},
    )
    assert result["type"] is FlowResultType.FORM
    fields = probatio.to_field_list(
        result["data_schema"], custom_serializer=cv.custom_serializer
    )
    advanced = next(field for field in fields if field["name"] == "advanced")
    for field in advanced["schema"]:
        assert (
            field["description"]["suggested_value"] == ADVANCED_SETTINGS[field["name"]]
        )
