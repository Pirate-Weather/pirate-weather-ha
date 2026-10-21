"""Test inline forecast forms and compatibility with saved configurations."""

from __future__ import annotations

import probatio
import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_MONITORED_CONDITIONS
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from custom_components.pirateweather.const import DOMAIN, PW_PLATFORM
from custom_components.pirateweather.forecast_config import (
    CONF_FORECAST,
    CONF_HOURLY_FORECAST,
    DAILY_DAYS,
    DAILY_ENABLED,
    HOURLY_COUNT,
    HOURLY_ENABLED,
    HOURLY_END,
    HOURLY_HOURS,
    HOURLY_INTERVAL,
    HOURLY_SCHEDULE,
    HOURLY_START,
)

SENSOR_SETTINGS = {
    CONF_FORECAST: "0,2",
    CONF_HOURLY_FORECAST: "0,6,12",
    CONF_MONITORED_CONDITIONS: ["temperature", "humidity"],
}
FORM_SETTINGS = {
    DAILY_ENABLED: True,
    DAILY_DAYS: ["0", "2"],
    HOURLY_ENABLED: True,
    HOURLY_SCHEDULE: "specific",
    HOURLY_HOURS: ["0", "6", "12"],
    CONF_MONITORED_CONDITIONS: ["temperature", "humidity"],
}


def serialized_fields(result):
    """Return the form fields as received by the frontend."""
    return {
        field["name"]: field
        for field in probatio.to_field_list(
            result["data_schema"], custom_serializer=cv.custom_serializer
        )
    }


async def start_flow(hass, entry, flow_type):
    """Initialize either form through Home Assistant's flow manager."""
    if flow_type == "setup":
        manager = hass.config_entries.flow
        result = await manager.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    else:
        entry.add_to_hass(hass)
        manager = hass.config_entries.options
        result = await manager.async_init(entry.entry_id)
    return manager, result


@pytest.mark.parametrize("flow_type", ["setup", "options"])
async def test_sensor_visibility_schema(hass, mock_config_entry, flow_type):
    """Expose native conditions for platform, enabled groups, and hourly mode."""
    _, result = await start_flow(hass, mock_config_entry, flow_type)
    fields = serialized_fields(result)
    platform = fields[PW_PLATFORM]
    assert platform["default"] == "Weather"
    assert platform["selector"]["select"]["multiple"] is False
    assert platform["selector"]["select"]["options"] == ["Sensor", "Weather", "Both"]
    sensors = {"field": PW_PLATFORM, "operator": "in", "value": ["Sensor", "Both"]}
    for key in [CONF_MONITORED_CONDITIONS, DAILY_ENABLED, HOURLY_ENABLED]:
        assert fields[key]["visible"] == sensors
    assert fields[DAILY_DAYS]["visible"] == {
        "condition": "and",
        "conditions": [sensors, {"field": DAILY_ENABLED, "value": True}],
    }
    assert fields[HOURLY_SCHEDULE]["visible"]["conditions"] == [
        sensors,
        {"field": HOURLY_ENABLED, "value": True},
    ]
    for key, mode in [
        (HOURLY_HOURS, "specific"),
        (HOURLY_COUNT, "next"),
        (HOURLY_START, "interval"),
        (HOURLY_END, "interval"),
        (HOURLY_INTERVAL, "interval"),
    ]:
        assert fields[key]["visible"]["conditions"] == [
            sensors,
            {"field": HOURLY_ENABLED, "value": True},
            {"field": HOURLY_SCHEDULE, "value": mode},
        ]
    assert fields[DAILY_DAYS]["selector"]["select"]["options"] == list(
        map(str, range(8))
    )
    assert fields[CONF_MONITORED_CONDITIONS]["selector"]["select"]["multiple"] is True
    assert "visible" not in fields[CONF_API_KEY]
    assert CONF_FORECAST not in fields
    assert CONF_HOURLY_FORECAST not in fields


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
    """Preserve platform and shared conditions storage, reviewing forecasts only."""
    manager, result = await start_flow(hass, mock_config_entry, flow_type)
    values = {
        CONF_API_KEY: mock_config_entry.data[CONF_API_KEY],
        PW_PLATFORM: selection,
        "advanced": {},
    }
    if selection != "Weather":
        values.update(FORM_SETTINGS)
    result = await manager.async_configure(result["flow_id"], values)
    if selection != "Weather":
        assert result["step_id"] == "forecast_summary"
        result = await manager.async_configure(result["flow_id"], {})
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
    """Switching to weather only retains legacy forecasts and schedule preferences."""
    mock_config_entry.add_to_hass(hass)
    saved = {
        **SENSOR_SETTINGS,
        HOURLY_SCHEDULE: "interval",
        HOURLY_START: 0,
        HOURLY_END: 12,
        HOURLY_INTERVAL: 6,
    }
    if source == "data":
        hass.config_entries.async_update_entry(
            mock_config_entry, data={**mock_config_entry.data, **saved}
        )
    else:
        hass.config_entries.async_update_entry(mock_config_entry, options=saved)
    unique_id = mock_config_entry.unique_id
    manager = hass.config_entries.options
    result = await manager.async_init(mock_config_entry.entry_id)
    values = {PW_PLATFORM: "Weather", "advanced": {}}
    if clear_hidden_fields:
        values.update(
            {
                DAILY_ENABLED: False,
                DAILY_DAYS: [],
                HOURLY_ENABLED: False,
                HOURLY_HOURS: [],
                CONF_MONITORED_CONDITIONS: [],
            }
        )
    result = await manager.async_configure(result["flow_id"], values)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    for key, value in saved.items():
        assert mock_config_entry.options[key] == value
    result = await manager.async_init(mock_config_entry.entry_id)
    fields = serialized_fields(result)
    assert fields[DAILY_DAYS]["default"] == ["0", "2"]
    assert fields[HOURLY_SCHEDULE]["default"] == "interval"
    result = await manager.async_configure(
        result["flow_id"], {PW_PLATFORM: "Both", "advanced": {}}
    )
    assert result["step_id"] == "forecast_summary"
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[PW_PLATFORM] == ["Sensor", "Weather"]
    for key, value in saved.items():
        assert mock_config_entry.options[key] == value
    assert mock_config_entry.unique_id == unique_id


async def test_validation_error_retains_sensor_form_values(hass, mock_config_entry):
    """A failed save retains edited platform and forecast scheduling values."""
    manager, result = await start_flow(hass, mock_config_entry, "options")
    result = await manager.async_configure(
        result["flow_id"],
        {CONF_API_KEY: " ", PW_PLATFORM: "Both", "advanced": {}, **FORM_SETTINGS},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_API_KEY: "invalid_api_key"}
    fields = serialized_fields(result)
    assert fields[PW_PLATFORM]["description"]["suggested_value"] == "Both"
    for key, value in FORM_SETTINGS.items():
        assert fields[key]["description"]["suggested_value"] == value


@pytest.mark.parametrize(
    ("platforms", "selection"),
    [(["Weather"], "Weather"), (["Sensor"], "Sensor"), (["Weather", "Sensor"], "Both")],
)
async def test_legacy_platforms_and_forecasts_in_options(
    hass, mock_config_entry, mock_get_clientsession_config_flow, *, platforms, selection
):
    """Existing platform and YAML forecast lists populate the new controls."""
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
    manager = hass.config_entries.options
    result = await manager.async_init(mock_config_entry.entry_id)
    fields = serialized_fields(result)
    assert fields[PW_PLATFORM]["default"] == selection
    assert fields[DAILY_ENABLED]["default"] is True
    assert fields[DAILY_DAYS]["default"] == ["0", "2"]
    assert fields[HOURLY_ENABLED]["default"] is True
    assert fields[HOURLY_HOURS]["default"] == ["0", "6", "12"]
    result = await manager.async_configure(
        result["flow_id"], {PW_PLATFORM: "Both", "advanced": {}}
    )
    assert result["step_id"] == "forecast_summary"
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_FORECAST] == "0,2"
    assert mock_config_entry.options[CONF_HOURLY_FORECAST] == "0,6,12"


@pytest.mark.parametrize("flow_type", ["setup", "options"])
@pytest.mark.parametrize(
    ("controls", "days", "hours"),
    [
        ({DAILY_ENABLED: True, DAILY_DAYS: ["7", "0", "1"]}, "0,1,7", ""),
        (
            {
                HOURLY_ENABLED: True,
                HOURLY_SCHEDULE: "specific",
                HOURLY_HOURS: ["167", "0", "6"],
            },
            "",
            "0,6,167",
        ),
        (
            {HOURLY_ENABLED: True, HOURLY_SCHEDULE: "next", HOURLY_COUNT: 4},
            "",
            "1,2,3,4",
        ),
        (
            {
                HOURLY_ENABLED: True,
                HOURLY_SCHEDULE: "interval",
                HOURLY_START: 0,
                HOURLY_END: 12,
                HOURLY_INTERVAL: 6,
            },
            "",
            "0,6,12",
        ),
        (
            {
                HOURLY_ENABLED: True,
                HOURLY_SCHEDULE: "interval",
                HOURLY_START: 3,
                HOURLY_END: 14,
                HOURLY_INTERVAL: 6,
            },
            "",
            "3,9",
        ),
        (
            {
                HOURLY_ENABLED: True,
                HOURLY_SCHEDULE: "interval",
                HOURLY_START: 167,
                HOURLY_END: 167,
                HOURLY_INTERVAL: 1,
            },
            "",
            "167",
        ),
    ],
)
async def test_forecast_schedules(
    hass,
    mock_config_entry,
    mock_get_clientsession_config_flow,
    *,
    flow_type,
    controls,
    days,
    hours,
):
    """Save each schedule as the same offsets used by existing sensor IDs."""
    manager, result = await start_flow(hass, mock_config_entry, flow_type)
    result = await manager.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: mock_config_entry.data[CONF_API_KEY],
            PW_PLATFORM: "Sensor",
            "advanced": {},
            CONF_MONITORED_CONDITIONS: ["temperature"],
            **controls,
        },
    )
    assert result["step_id"] == "forecast_summary"
    if flow_type == "options":
        assert not mock_config_entry.options
    result = await manager.async_configure(result["flow_id"], {})
    assert result["data"][CONF_FORECAST] == days
    assert result["data"][CONF_HOURLY_FORECAST] == hours
    for key, value in controls.items():
        assert result["data"][key] == value
    if flow_type == "options":
        reopened = await manager.async_init(mock_config_entry.entry_id)
        fields = serialized_fields(reopened)
        for key, value in controls.items():
            assert fields[key]["default"] == value


@pytest.mark.parametrize("flow_type", ["setup", "options"])
async def test_summary_counts_supported_conditions(
    hass, mock_config_entry, mock_get_clientsession_config_flow, flow_type
):
    """Preview mirrors runtime filtering without splitting the conditions list."""
    manager, result = await start_flow(hass, mock_config_entry, flow_type)
    conditions = ["temperature", "precip_accumulation", "nearest_storm_distance"]
    # Temperature: hourly/current; accumulation: daily/hourly; storm: current only.
    result = await manager.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: mock_config_entry.data[CONF_API_KEY],
            PW_PLATFORM: "Both",
            "advanced": {},
            **FORM_SETTINGS,
            CONF_MONITORED_CONDITIONS: conditions,
        },
    )
    assert result["description_placeholders"] == {
        "daily_count": "2",
        "hourly_count": "6",
        "forecast_total": "8",
    }
    result = await manager.async_configure(result["flow_id"], {})
    assert result["data"][CONF_MONITORED_CONDITIONS] == conditions


@pytest.mark.parametrize("flow_type", ["setup", "options"])
@pytest.mark.parametrize(
    ("controls", "errors"),
    [
        ({DAILY_ENABLED: True, DAILY_DAYS: []}, {DAILY_DAYS: "select_forecast_days"}),
        (
            {HOURLY_ENABLED: True, HOURLY_HOURS: []},
            {HOURLY_HOURS: "select_forecast_hours"},
        ),
        (
            {
                HOURLY_ENABLED: True,
                HOURLY_SCHEDULE: "interval",
                HOURLY_START: 24,
                HOURLY_END: 3,
            },
            {HOURLY_END: "invalid_hourly_range"},
        ),
    ],
)
async def test_forecast_validation(
    hass,
    mock_config_entry,
    mock_get_clientsession_config_flow,
    *,
    flow_type,
    controls,
    errors,
):
    """Explain invalid selections and allow correcting the same form."""
    manager, result = await start_flow(hass, mock_config_entry, flow_type)
    values = {
        CONF_API_KEY: mock_config_entry.data[CONF_API_KEY],
        PW_PLATFORM: "Sensor",
        "advanced": {},
        **controls,
    }
    result = await manager.async_configure(result["flow_id"], values)
    assert result["errors"] == errors
    fields = serialized_fields(result)
    for key, value in controls.items():
        assert fields[key]["description"]["suggested_value"] == value
    result = await manager.async_configure(
        result["flow_id"],
        {**values, DAILY_DAYS: ["0"], HOURLY_HOURS: ["1"], HOURLY_END: 24},
    )
    assert result["step_id"] == "forecast_summary"
    manager.async_abort(result["flow_id"])


@pytest.mark.parametrize(
    ("key", "value"),
    [
        (DAILY_DAYS, ["8"]),
        (HOURLY_HOURS, ["168"]),
        (HOURLY_COUNT, 0),
        (HOURLY_COUNT, 168),
        (HOURLY_COUNT, 2.5),
        (HOURLY_START, -1),
        (HOURLY_END, 168),
        (HOURLY_INTERVAL, 0),
        (HOURLY_INTERVAL, 1.5),
    ],
)
async def test_invalid_forecast_bounds(hass, mock_config_entry, key, value):
    """Reject offsets outside the API's forecast window and fractional hours."""
    manager, result = await start_flow(hass, mock_config_entry, "options")
    with pytest.raises(InvalidData):
        await manager.async_configure(
            result["flow_id"], {PW_PLATFORM: "Both", "advanced": {}, key: value}
        )


async def test_disabling_forecasts_preserves_choices(
    hass, mock_config_entry, mock_get_clientsession_config_flow
):
    """Disabling forecasts clears runtime offsets but keeps choices for reenabling."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={**SENSOR_SETTINGS, **FORM_SETTINGS, PW_PLATFORM: ["Sensor"]},
    )
    manager = hass.config_entries.options
    result = await manager.async_init(mock_config_entry.entry_id)
    result = await manager.async_configure(
        result["flow_id"], {"advanced": {}, DAILY_ENABLED: False, HOURLY_ENABLED: False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_FORECAST] == ""
    assert result["data"][CONF_HOURLY_FORECAST] == ""
    assert (
        result["data"][CONF_MONITORED_CONDITIONS]
        == SENSOR_SETTINGS[CONF_MONITORED_CONDITIONS]
    )
    result = await manager.async_init(mock_config_entry.entry_id)
    fields = serialized_fields(result)
    assert fields[DAILY_DAYS]["default"] == FORM_SETTINGS[DAILY_DAYS]
    assert fields[HOURLY_HOURS]["default"] == FORM_SETTINGS[HOURLY_HOURS]


async def test_cancel_forecast_preview_does_not_save(
    hass, mock_config_entry, mock_get_clientsession_config_flow
):
    """Cancellation at review leaves existing settings and conditions untouched."""
    manager, result = await start_flow(hass, mock_config_entry, "options")
    result = await manager.async_configure(
        result["flow_id"], {PW_PLATFORM: "Both", "advanced": {}, **FORM_SETTINGS}
    )
    assert result["step_id"] == "forecast_summary"
    manager.async_abort(result["flow_id"])
    assert not mock_config_entry.options


async def test_yaml_forecasts_import_without_review(
    hass, mock_config_entry_data, mock_get_clientsession_config_flow
):
    """Legacy YAML imports remain noninteractive and retain forecast offsets."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={**mock_config_entry_data, **SENSOR_SETTINGS, PW_PLATFORM: ["Sensor"]},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    for key, value in SENSOR_SETTINGS.items():
        assert result["data"][key] == value


async def test_legacy_entity_ids_survive_options_save(
    hass, mock_config_entry, mock_get_clientsession, mock_get_clientsession_config_flow
):
    """Saving a legacy entry through new controls preserves current and forecast IDs."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        data={
            **mock_config_entry.data,
            **SENSOR_SETTINGS,
            PW_PLATFORM: ["Sensor"],
            CONF_FORECAST: "0",
            CONF_HOURLY_FORECAST: "0",
        },
    )
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)

    def registered_entities():
        return {
            entity.unique_id: entity.entity_id
            for entity in er.async_entries_for_config_entry(
                registry, mock_config_entry.entry_id
            )
        }

    before = registered_entities()
    assert set(before) == {
        "test_unique_id-sensor-temperature",
        "test_unique_id-sensor-humidity",
        "test_unique_id-sensor-humidity-daily-0",
        "test_unique_id-sensor-temperature-hourly-0",
        "test_unique_id-sensor-humidity-hourly-0",
    }
    manager = hass.config_entries.options
    result = await manager.async_init(mock_config_entry.entry_id)
    result = await manager.async_configure(result["flow_id"], {"advanced": {}})
    assert result["description_placeholders"] == {
        "daily_count": "1",
        "hourly_count": "2",
        "forecast_total": "3",
    }
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert registered_entities() == before
    for entity_id in before.values():
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state not in {"unknown", "unavailable"}
