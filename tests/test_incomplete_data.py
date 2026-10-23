"""Regressions for incomplete responses and failed weather updates."""

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientError

from custom_components.pirateweather.const import DEFAULT_ENDPOINT
from custom_components.pirateweather.forecast_models import Forecast
from custom_components.pirateweather.sensor import SENSOR_TYPES, PirateWeatherSensor
from custom_components.pirateweather.weather import (
    PirateWeather,
    _map_daily_forecast,
    _map_day_night_forecast,
    _map_hourly_forecast,
)
from custom_components.pirateweather.weather_update_coordinator import (
    WeatherUpdateCoordinator,
)


@pytest.fixture
def coordinator(hass, mock_config_entry):
    """Create the real coordinator with a synthetic API key."""
    return WeatherUpdateCoordinator(
        api_key="test-api-key",
        latitude=37.8267,
        longitude=-122.4233,
        scan_interval=timedelta(minutes=20),
        language="en",
        endpoint=DEFAULT_ENDPOINT,
        units="si",
        hass=hass,
        config_entry=mock_config_entry,
        models=None,
    )


def make_sensor(coordinator, condition="temperature", **kwargs):
    """Create a sensor without changing entity registry state."""
    return PirateWeatherSensor(
        coordinator,
        condition,
        "Test Weather",
        f"test-{condition}",
        forecast_day=kwargs.get("forecast_day"),
        forecast_hour=kwargs.get("forecast_hour"),
        description=SENSOR_TYPES[condition],
        request_units="si",
        output_round="No",
        service_id="test-service",
    )


def make_weather(coordinator):
    """Create the weather entity using the actual model accessors."""
    return PirateWeather(
        "Test Weather", "test-weather", "hourly", coordinator, "No", "test-service"
    )


async def test_availability_tracks_failed_refresh_and_recovery(
    coordinator, mock_get_clientsession, mock_aiohttp_session
):
    """Cached data must not keep entities available after a failed poll."""
    await coordinator.async_refresh()
    weather = make_weather(coordinator)
    sensor = make_sensor(coordinator)
    cached = coordinator.data
    assert weather.available and sensor.available

    mock_aiohttp_session.get.side_effect = ClientError("temporary outage")
    await coordinator.async_refresh()
    assert coordinator.data is cached
    assert not weather.available
    assert not sensor.available

    mock_aiohttp_session.get.side_effect = None
    await coordinator.async_refresh()
    assert weather.available and sensor.available


@pytest.mark.parametrize("error_type", [ClientError, TimeoutError, ValueError])
async def test_request_error_does_not_log_api_key(
    coordinator, mock_get_clientsession, mock_aiohttp_session, caplog, error_type
):
    """Transport exception text can contain the authenticated request URL."""
    mock_aiohttp_session.get.side_effect = error_type(
        "https://example.invalid/forecast/test-api-key/0,0"
    )
    await coordinator.async_refresh()
    assert not coordinator.last_update_success
    assert "test-api-key" not in str(coordinator.last_exception)
    assert "test-api-key" not in caplog.text


async def test_cancellation_closes_response(
    coordinator, mock_get_clientsession, mock_aiohttp_session
):
    """Cancellation must propagate while releasing the HTTP response."""
    context = mock_aiohttp_session.get.return_value
    started = asyncio.Event()

    async def wait_for_json():
        """Wait for task cancellation while reading the response body."""
        started.set()
        await asyncio.Event().wait()

    context.mock_resp.json.side_effect = wait_for_json
    with patch.object(type(context), "__aexit__", new_callable=AsyncMock) as exit_mock:
        exit_mock.return_value = False
        task = asyncio.create_task(coordinator.async_refresh())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        exit_mock.assert_awaited_once()


@pytest.mark.parametrize("payload", [None, [], {}, {"currently": None}])
async def test_invalid_success_payload_preserves_cached_data(
    coordinator, mock_get_clientsession, mock_aiohttp_session, payload
):
    """HTTP 200 alone must not replace a usable forecast with an error body."""
    await coordinator.async_refresh()
    cached = coordinator.data
    response = mock_aiohttp_session.get.return_value.mock_resp
    response.json.return_value = payload
    await coordinator.async_refresh()
    assert not coordinator.last_update_success
    assert coordinator.data is cached


@pytest.mark.parametrize(
    "property_name",
    [
        "native_temperature",
        "native_apparent_temperature",
        "cloud_coverage",
        "humidity",
        "native_dew_point",
        "native_wind_speed",
        "native_wind_gust_speed",
        "wind_bearing",
        "ozone",
        "native_pressure",
        "native_visibility",
    ],
)
@pytest.mark.parametrize("value", [None, -999, float("nan"), float("inf")])
def test_missing_current_measurements_are_unknown(
    coordinator, mock_pirate_weather_response, property_name, value
):
    """Missing and sentinel measurements must not be rounded or scaled."""
    payload = mock_pirate_weather_response
    payload["currently"] = dict.fromkeys(payload["currently"], value)
    # Keep the model's timestamp valid; this test concerns measurements.
    payload["currently"]["time"] = 1700000000
    coordinator.data = Forecast(payload, None, {})
    assert getattr(make_weather(coordinator), property_name) is None


@pytest.mark.parametrize(
    "mapper", [_map_daily_forecast, _map_day_night_forecast, _map_hourly_forecast]
)
@pytest.mark.parametrize("value", [None, -999, float("nan"), float("inf")])
def test_forecast_mapping_tolerates_missing_numbers(mapper, value):
    """A valid timestamp can accompany missing optional forecast values."""
    point = SimpleNamespace(
        d={
            "time": 1700000000,
            "temperature": value,
            "temperatureHigh": value,
            "temperatureLow": value,
            "precipAccumulation": value,
            "precipProbability": value,
            "humidity": value,
            "cloudCover": value,
            "windSpeed": value,
            "windGust": value,
            "windBearing": value,
            "dewPoint": value,
            "pressure": value,
            "uvIndex": value,
        }
    )
    result = mapper(point, "si")
    for key, measurement in result.items():
        if key not in {"datetime", "condition", "is_daytime"}:
            assert measurement is None, key


@pytest.mark.parametrize("mode", ["daily", "hourly"])
@pytest.mark.parametrize("length", [0, 1])
def test_short_forecast_sensor_is_unknown(
    coordinator, mock_pirate_weather_response, mode, length
):
    """Configured forecast indices may exceed the available horizon."""
    payload = mock_pirate_weather_response
    payload[mode]["data"] = payload[mode]["data"][:length]
    coordinator.data = Forecast(payload, None, {})
    kwargs = {"forecast_day" if mode == "daily" else "forecast_hour": 6}
    assert make_sensor(coordinator, **kwargs).native_value is None


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("condition", ["temperature", "humidity", "precip_intensity"])
def test_sensor_rejects_nonfinite_numbers(coordinator, value, condition):
    """Nonfinite values are not valid Home Assistant numeric states."""
    sensor = make_sensor(coordinator, condition)
    key = {
        "temperature": "temperature",
        "humidity": "humidity",
        "precip_intensity": "precipIntensity",
    }[condition]
    assert sensor.get_state({key: value}) is None


def test_valid_measurements_keep_rounding_and_unit_conversion(
    coordinator, mock_pirate_weather_response
):
    """The missing-value guard must preserve ordinary zero and negative values."""
    payload = mock_pirate_weather_response
    payload["currently"].update(temperature=-1.234, humidity=0, cloudCover=0.125)
    coordinator.data = Forecast(payload, None, {})
    weather = make_weather(coordinator)
    assert weather.native_temperature == -1.23
    assert weather.humidity == 0
    assert weather.cloud_coverage == 12.5
    assert make_sensor(coordinator, "humidity").native_value == 0
    assert (
        make_sensor(coordinator, "snow_intensity").get_state({"snowIntensity": 0.12})
        == 1.2
    )


def test_alert_attributes_before_first_read(coordinator):
    """Home Assistant can request attributes before the first native value."""
    assert make_sensor(coordinator, "alerts").extra_state_attributes["attribution"]
