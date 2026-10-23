"""Test forecast access without hidden HTTP requests."""

from unittest.mock import Mock, patch

import pytest

from custom_components.pirateweather.forecast_models import (
    Forecast,
    PirateWeatherDataBlock,
    PirateWeatherDataPoint,
    PirateWeatherFlagsBlock,
)


@pytest.mark.parametrize(
    "section", ["currently", "minutely", "hourly", "daily", "day_night", "flags"]
)
@pytest.mark.parametrize("explicit_null", [False, True])
def test_missing_section_does_not_fetch(section, explicit_null):
    """An absent optional section must stay empty until a coordinator update."""
    data = {section: None} if explicit_null else {}
    forecast = Forecast(data, Mock(url="https://example.invalid/forecast/test"), {})

    with patch(
        "requests.get", side_effect=AssertionError("Unexpected synchronous HTTP")
    ) as get:
        block = getattr(forecast, section)()

    get.assert_not_called()
    assert forecast.json == data
    if section == "currently":
        assert isinstance(block, PirateWeatherDataPoint)
        assert block.temperature is None
    elif section == "flags":
        assert isinstance(block, PirateWeatherFlagsBlock)
        assert block.sources == []
    else:
        assert isinstance(block, PirateWeatherDataBlock)
        assert block.data == []


@pytest.mark.parametrize("sources", [None, [], ["gfs"]])
def test_flags_sources_can_be_missing_or_null(sources):
    """Missing source metadata must not break otherwise usable weather data."""
    assert PirateWeatherFlagsBlock({"sources": sources}).sources == (sources or [])
    assert PirateWeatherFlagsBlock({}).sources == []


def test_present_data_is_preserved_without_network():
    """Existing current and forecast values must keep their original meaning."""
    data = {
        "currently": {"time": 1, "temperature": 20},
        "hourly": {"data": [{"time": 2, "temperature": 21}]},
        "daily": {"data": [{"time": 3, "temperatureHigh": 22}]},
        "flags": {"sources": ["gfs"]},
    }
    forecast = Forecast(data, Mock(), {})

    with patch(
        "requests.get", side_effect=AssertionError("Unexpected synchronous HTTP")
    ) as get:
        assert forecast.currently().temperature == 20
        assert forecast.hourly().data[0].temperature == 21
        assert forecast.daily().data[0].temperatureHigh == 22
        assert forecast.flags().sources == ["gfs"]

    get.assert_not_called()
    assert forecast.json == data
