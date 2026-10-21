"""Test immutable instance identities and separate configuration duplicate checks."""

from __future__ import annotations

from uuid import UUID

import pytest
from homeassistant import config_entries
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MONITORED_CONDITIONS,
)
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.pirateweather.const import (
    CONF_ENDPOINT,
    CONF_INSTANCE_ID,
    CONF_LANGUAGE,
    CONF_MODELS,
    CONF_UNITS,
    DOMAIN,
    PW_PLATFORM,
)
from custom_components.pirateweather.forecast_config import (
    CONF_FORECAST,
    CONF_HOURLY_FORECAST,
    DAILY_DAYS,
    DAILY_ENABLED,
    HOURLY_ENABLED,
    HOURLY_HOURS,
)


def setup_values(data):
    """Build a form submission with both platforms and supported forecasts."""
    return {
        CONF_API_KEY: data[CONF_API_KEY],
        CONF_LATITUDE: data[CONF_LATITUDE],
        CONF_LONGITUDE: data[CONF_LONGITUDE],
        PW_PLATFORM: "both",
        CONF_MONITORED_CONDITIONS: ["humidity"],
        DAILY_ENABLED: True,
        DAILY_DAYS: ["0"],
        HOURLY_ENABLED: True,
        HOURLY_HOURS: ["0"],
        "advanced": {},
    }


async def create_instance(hass, data, source=config_entries.SOURCE_USER):
    """Complete either UI setup or a noninteractive YAML import."""
    manager = hass.config_entries.flow
    if source == config_entries.SOURCE_IMPORT:
        result = await manager.async_init(
            DOMAIN,
            context={"source": source},
            data={
                **data,
                PW_PLATFORM: ["Sensor", "Weather"],
                CONF_MONITORED_CONDITIONS: ["humidity"],
                CONF_FORECAST: "0",
                CONF_HOURLY_FORECAST: "0",
            },
        )
    else:
        result = await manager.async_init(DOMAIN, context={"source": source})
        result = await manager.async_configure(result["flow_id"], setup_values(data))
        assert result["step_id"] == "forecast_summary"
        result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    return next(
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.data[CONF_INSTANCE_ID] == result["data"][CONF_INSTANCE_ID]
    )


@pytest.mark.parametrize(
    "source", [config_entries.SOURCE_USER, config_entries.SOURCE_IMPORT]
)
async def test_new_entries_have_uuid_identity(
    hass,
    mock_config_entry_data,
    mock_get_clientsession_config_flow,
    mock_get_clientsession,
    source,
):
    """UI and YAML entries use UUIDv4 identities for entities and service devices."""
    entry = await create_instance(hass, mock_config_entry_data, source)
    instance_id = entry.data[CONF_INSTANCE_ID]
    assert UUID(instance_id).version == 4
    assert UUID(instance_id).hex == instance_id
    assert entry.unique_id == f"pw-{instance_id}"
    registry = er.async_get(hass)
    identities = {
        entity.unique_id
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    assert identities == {
        entry.unique_id,
        f"{entry.unique_id}-sensor-humidity",
        f"{entry.unique_id}-sensor-humidity-daily-0",
        f"{entry.unique_id}-sensor-humidity-hourly-0",
    }
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry.unique_id), entry.entry_id
    )
    assert device is not None


async def test_uuid_identity_survives_options_and_rename(
    hass,
    mock_config_entry_data,
    mock_get_clientsession_config_flow,
    mock_get_clientsession,
):
    """Location, credentials, advanced options and title edits preserve registry IDs."""
    entry = await create_instance(hass, mock_config_entry_data)
    registry = er.async_get(hass)

    def identities():
        return {
            entity.unique_id: (entity.entity_id, entity.device_id)
            for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        }

    before = identities()
    original_data = dict(entry.data)
    unique_id = entry.unique_id
    hass.config_entries.async_update_entry(entry, title="Renamed forecast")
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    fields = {str(key) for key in flow["data_schema"].schema}
    assert CONF_INSTANCE_ID not in fields
    flow = await hass.config_entries.options.async_configure(
        flow["flow_id"],
        {
            CONF_API_KEY: "rotated_key",
            CONF_LATITUDE: mock_config_entry_data[CONF_LATITUDE] + 1,
            CONF_LONGITUDE: mock_config_entry_data[CONF_LONGITUDE] + 1,
            CONF_LANGUAGE: "fr",
            "advanced": {
                CONF_MODELS: "gfs",
                CONF_UNITS: "si",
                CONF_ENDPOINT: "https://alternate.example",
            },
        },
    )
    assert flow["step_id"] == "forecast_summary"
    result = await hass.config_entries.options.async_configure(flow["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.unique_id == unique_id
    assert entry.data == original_data
    assert CONF_INSTANCE_ID not in entry.options
    assert entry.title == "Renamed forecast"
    assert identities() == before
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert identities() == before
    assert entry.unique_id == unique_id


async def test_recreating_entry_generates_new_uuid(
    hass,
    mock_config_entry_data,
    mock_get_clientsession_config_flow,
    mock_get_clientsession,
):
    """Deleting and recreating identical configuration creates a new identity."""
    first = await create_instance(hass, mock_config_entry_data)
    first_id = first.unique_id
    assert await hass.config_entries.async_remove(first.entry_id)
    second = await create_instance(hass, mock_config_entry_data)
    assert first_id != second.unique_id
    assert first.entry_id != second.entry_id


@pytest.mark.parametrize(
    ("location", "platform", "duplicate"),
    [
        ("old", "weather", False),
        ("new", "both", True),
        ("new", "weather", False),
        ("new", ["Weather", "Sensor"], True),
    ],
)
async def test_duplicates_use_effective_options(
    hass,
    mock_config_entry,
    mock_get_clientsession_config_flow,
    mock_get_clientsession,
    *,
    location,
    platform,
    duplicate,
):
    """Compare current location and platform choices, with options overriding data."""
    mock_config_entry.add_to_hass(hass)
    data = mock_config_entry.data
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            CONF_LATITUDE: data[CONF_LATITUDE] + 1,
            CONF_LONGITUDE: data[CONF_LONGITUDE] + 1,
            PW_PLATFORM: ["Sensor", "Weather"],
        },
    )
    manager = hass.config_entries.flow
    result = await manager.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await manager.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: data[CONF_API_KEY],
            CONF_LATITUDE: data[CONF_LATITUDE] + (location == "new"),
            CONF_LONGITUDE: data[CONF_LONGITUDE] + (location == "new"),
            PW_PLATFORM: platform,
            "advanced": {},
        },
    )
    if duplicate:
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"
    else:
        assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.unique_id == "test_unique_id"
    assert CONF_INSTANCE_ID not in mock_config_entry.data


async def test_duplicates_rechecked_after_review(
    hass,
    mock_config_entry_data,
    mock_get_clientsession_config_flow,
    mock_get_clientsession,
):
    """Two setup flows cannot save the same configuration after separate previews."""
    manager = hass.config_entries.flow
    previews = []
    for _ in range(2):
        flow = await manager.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        flow = await manager.async_configure(
            flow["flow_id"], setup_values(mock_config_entry_data)
        )
        assert flow["step_id"] == "forecast_summary"
        previews.append(flow)
    first = await manager.async_configure(previews[0]["flow_id"], {})
    assert first["type"] is FlowResultType.CREATE_ENTRY
    second = await manager.async_configure(previews[1]["flow_id"], {})
    assert second["type"] is FlowResultType.ABORT
    assert second["reason"] == "already_configured"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_validation_retry_keeps_instance_uuid(
    hass,
    mock_config_entry_data,
    mock_get_clientsession_config_flow,
    mock_get_clientsession,
):
    """Correcting a forecast selection does not regenerate the pending identity."""
    manager = hass.config_entries.flow
    flow = await manager.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    values = setup_values(mock_config_entry_data)
    flow = await manager.async_configure(flow["flow_id"], {**values, DAILY_DAYS: []})
    assert flow["errors"] == {DAILY_DAYS: "select_forecast_days"}
    identity = manager.async_get(flow["flow_id"])["context"]["unique_id"]
    flow = await manager.async_configure(flow["flow_id"], values)
    flow = await manager.async_configure(flow["flow_id"], {})
    assert flow["type"] is FlowResultType.CREATE_ENTRY
    assert flow["result"].unique_id == identity
    assert identity == f"pw-{flow['data'][CONF_INSTANCE_ID]}"
