"""Test inline sensor settings and compatibility with saved configurations."""

from __future__ import annotations

import probatio
import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_MONITORED_CONDITIONS
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_validation as cv

from custom_components.pirateweather.config_flow import (
    CONF_FORECAST,
    CONF_HOURLY_FORECAST,
)
from custom_components.pirateweather.const import DOMAIN, PW_PLATFORM

SENSOR_SETTINGS = {
    CONF_FORECAST: "0,2",
    CONF_HOURLY_FORECAST: "0,6,12",
    CONF_MONITORED_CONDITIONS: ["temperature", "humidity"],
}


@pytest.mark.parametrize("flow_type", ["setup", "options"])
async def test_sensor_visibility_schema(hass, mock_config_entry, flow_type):
    """Send frontend conditions referencing the actual platform selector values."""
    if flow_type == "setup":
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    else:
        mock_config_entry.add_to_hass(hass)
        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )

    fields = {
        field["name"]: field
        for field in probatio.to_field_list(
            result["data_schema"], custom_serializer=cv.custom_serializer
        )
    }
    platform = fields[PW_PLATFORM]
    assert platform["default"] == "Weather"
    assert platform["selector"]["select"]["multiple"] is False
    assert platform["selector"]["select"]["options"] == ["Sensor", "Weather", "Both"]
    for key in SENSOR_SETTINGS:
        assert fields[key]["visible"] == {
            "field": PW_PLATFORM,
            "operator": "in",
            "value": ["Sensor", "Both"],
        }
    assert fields[CONF_MONITORED_CONDITIONS]["selector"]["select"]["multiple"] is True
    assert "visible" not in fields[CONF_API_KEY]


@pytest.mark.parametrize("flow_type", ["setup", "options"])
@pytest.mark.parametrize(
    ("selection", "platforms"),
    [("Weather", ["Weather"]), ("Sensor", ["Sensor"]), ("Both", ["Sensor", "Weather"])],
)
async def test_platform_selection_saved_as_list(
    hass,
    mock_config_entry,
    mock_get_clientsession_config_flow,
    *,
    flow_type,
    selection,
    platforms,
):
    """All form choices save the existing runtime format without extra steps."""
    if flow_type == "setup":
        manager = hass.config_entries.flow
        result = await manager.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    else:
        mock_config_entry.add_to_hass(hass)
        manager = hass.config_entries.options
        result = await manager.async_init(mock_config_entry.entry_id)

    values = {
        CONF_API_KEY: mock_config_entry.data[CONF_API_KEY],
        PW_PLATFORM: selection,
        "advanced": {},
    }
    if selection != "Weather":
        values.update(SENSOR_SETTINGS)
    result = await manager.async_configure(result["flow_id"], values)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][PW_PLATFORM] == platforms
    if selection != "Weather":
        for key, value in SENSOR_SETTINGS.items():
            assert result["data"][key] == value


@pytest.mark.parametrize("source", ["data", "options"])
@pytest.mark.parametrize("clear_hidden_fields", [False, True])
async def test_hidden_sensor_settings_preserved(
    hass,
    mock_config_entry,
    mock_get_clientsession_config_flow,
    *,
    source,
    clear_hidden_fields,
):
    """Turning sensors off and on retains settings from legacy data or options."""
    mock_config_entry.add_to_hass(hass)
    if source == "data":
        hass.config_entries.async_update_entry(
            mock_config_entry, data={**mock_config_entry.data, **SENSOR_SETTINGS}
        )
    else:
        hass.config_entries.async_update_entry(
            mock_config_entry, options=SENSOR_SETTINGS
        )
    unique_id = mock_config_entry.unique_id
    manager = hass.config_entries.options
    result = await manager.async_init(mock_config_entry.entry_id)
    values = {PW_PLATFORM: "Weather", "advanced": {}}
    if clear_hidden_fields:
        values.update(
            {
                CONF_FORECAST: "",
                CONF_HOURLY_FORECAST: "",
                CONF_MONITORED_CONDITIONS: [],
            }
        )
    result = await manager.async_configure(result["flow_id"], values)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    for key, value in SENSOR_SETTINGS.items():
        assert mock_config_entry.options[key] == value

    result = await manager.async_init(mock_config_entry.entry_id)
    defaults = result["data_schema"]({"advanced": {}})
    for key, value in SENSOR_SETTINGS.items():
        assert defaults[key] == value
    result = await manager.async_configure(
        result["flow_id"], {**defaults, PW_PLATFORM: "Both"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[PW_PLATFORM] == ["Sensor", "Weather"]
    for key, value in SENSOR_SETTINGS.items():
        assert mock_config_entry.options[key] == value
    assert mock_config_entry.unique_id == unique_id


async def test_validation_error_retains_sensor_form_values(hass, mock_config_entry):
    """A failed save retains a visible platform choice and edited sensor values."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_API_KEY: " ", PW_PLATFORM: "Both", "advanced": {}, **SENSOR_SETTINGS},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_API_KEY: "invalid_api_key"}
    fields = {
        field["name"]: field
        for field in probatio.to_field_list(
            result["data_schema"], custom_serializer=cv.custom_serializer
        )
    }
    assert fields[PW_PLATFORM]["description"]["suggested_value"] == "Both"
    for key, value in SENSOR_SETTINGS.items():
        assert fields[key]["description"]["suggested_value"] == value


@pytest.mark.parametrize(
    ("platforms", "selection"),
    [(["Weather"], "Weather"), (["Sensor"], "Sensor"), (["Weather", "Sensor"], "Both")],
)
async def test_legacy_platforms_and_forecasts_in_options(
    hass, mock_config_entry, mock_get_clientsession_config_flow, *, platforms, selection
):
    """Existing platform and YAML forecast lists remain editable and reloadable."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        data={
            **mock_config_entry.data,
            PW_PLATFORM: platforms,
            CONF_FORECAST: ["0", "2"],
            CONF_HOURLY_FORECAST: [0, 6, 12],
            CONF_MONITORED_CONDITIONS: ["temperature"],
        },
    )
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    fields = {
        field["name"]: field
        for field in probatio.to_field_list(
            result["data_schema"], custom_serializer=cv.custom_serializer
        )
    }
    assert fields[PW_PLATFORM]["default"] == selection
    assert fields[CONF_FORECAST]["default"] == "0,2"
    assert fields[CONF_HOURLY_FORECAST]["default"] == "0,6,12"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            PW_PLATFORM: "Both",
            "advanced": {},
            CONF_FORECAST: fields[CONF_FORECAST]["default"],
            CONF_HOURLY_FORECAST: fields[CONF_HOURLY_FORECAST]["default"],
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_FORECAST] == "0,2"
    assert mock_config_entry.options[CONF_HOURLY_FORECAST] == "0,6,12"
