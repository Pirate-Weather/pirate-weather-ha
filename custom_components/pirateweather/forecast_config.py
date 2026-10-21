"""Form controls for daily and hourly sensor offsets."""

from __future__ import annotations

from ast import literal_eval
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    Selector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import PW_PLATFORM

CONF_FORECAST = "forecast"
CONF_HOURLY_FORECAST = "hourly_forecast"
DAILY_ENABLED = "daily_forecast_enabled"
DAILY_DAYS = "forecast_days"
HOURLY_ENABLED = "hourly_forecast_enabled"
HOURLY_SCHEDULE = "hourly_schedule"
HOURLY_HOURS = "forecast_hours"
HOURLY_COUNT = "hourly_count"
HOURLY_START = "hourly_start"
HOURLY_END = "hourly_end"
HOURLY_INTERVAL = "hourly_interval"
MAX_DAY = 7
MAX_HOUR = 167


def forecast_offsets(value: Any) -> list[int]:
    """Read existing CSV or YAML lists without changing offset semantics."""
    if isinstance(value, str):
        value = value.strip()
    if value is None or value in ("", "None"):
        return []
    if isinstance(value, str):
        value = literal_eval(value) if value.startswith("[") else value.split(",")
    return sorted({int(item) for item in value})


def forecast_form_defaults(saved: Mapping[str, Any]) -> dict[str, Any]:
    """Restore scheduling preferences, falling back to legacy forecast offsets."""
    days = forecast_offsets(saved.get(CONF_FORECAST))
    hours = forecast_offsets(saved.get(CONF_HOURLY_FORECAST))
    return {
        DAILY_ENABLED: saved.get(DAILY_ENABLED, bool(days)),
        DAILY_DAYS: saved.get(DAILY_DAYS, [str(day) for day in days] or ["0", "1"]),
        HOURLY_ENABLED: saved.get(HOURLY_ENABLED, bool(hours)),
        HOURLY_SCHEDULE: saved.get(HOURLY_SCHEDULE, "specific"),
        HOURLY_HOURS: saved.get(
            HOURLY_HOURS, [str(hour) for hour in hours] or ["1", "3", "6", "12", "24"]
        ),
        HOURLY_COUNT: saved.get(HOURLY_COUNT, 6),
        HOURLY_START: saved.get(HOURLY_START, 3),
        HOURLY_END: saved.get(HOURLY_END, 24),
        HOURLY_INTERVAL: saved.get(HOURLY_INTERVAL, 3),
    }


class SensorSettingSelector(Selector):
    """Show a standard selector when sensors and its additional conditions apply."""

    def __init__(self, selector: Selector, *conditions: dict[str, Any]) -> None:
        """Wrap a selector with sensor-specific visibility conditions."""
        self._selector = selector
        self._conditions = conditions
        self.selector_type = selector.selector_type
        self.config = selector.config

    def __call__(self, data: Any) -> Any:
        """Validate the value with the wrapped selector."""
        return self._selector(data)

    def serialize(self) -> dict[str, Any]:
        """Use native ha-form conditions for inline visibility."""
        sensors = {
            "field": PW_PLATFORM,
            "operator": "in",
            "value": ["sensor", "both"],
        }
        visible = (
            {"condition": "and", "conditions": [sensors, *self._conditions]}
            if self._conditions
            else sensors
        )
        return {**self._selector.serialize(), "visible": visible}


class _HourNumberSelector(NumberSelector):
    """Validate whole-hour counts and offsets as well as their bounds."""

    def __init__(self, minimum: int) -> None:
        super().__init__(
            NumberSelectorConfig(
                min=minimum, max=MAX_HOUR, step=1, mode=NumberSelectorMode.BOX
            )
        )

    def __call__(self, data: Any) -> int:
        """Reject fractional hours instead of silently rounding them."""
        value = super().__call__(data)
        if not float(value).is_integer():
            raise vol.Invalid("Enter a whole number of hours")
        return int(value)


def forecast_schema(saved: Mapping[str, Any]) -> dict:
    """Build the forecast controls while keeping the conditions list shared."""
    defaults = forecast_form_defaults(saved)
    daily = {"field": DAILY_ENABLED, "value": True}
    hourly = {"field": HOURLY_ENABLED, "value": True}

    def number(name: str, minimum: int, schedule: str) -> tuple:
        return (
            vol.Optional(name, default=defaults[name]),
            SensorSettingSelector(
                _HourNumberSelector(minimum),
                hourly,
                {"field": HOURLY_SCHEDULE, "value": schedule},
            ),
        )

    return {
        vol.Optional(
            DAILY_ENABLED, default=defaults[DAILY_ENABLED]
        ): SensorSettingSelector(BooleanSelector()),
        vol.Optional(DAILY_DAYS, default=defaults[DAILY_DAYS]): SensorSettingSelector(
            SelectSelector(
                SelectSelectorConfig(
                    options=[str(day) for day in range(MAX_DAY + 1)],
                    multiple=True,
                    translation_key="forecast_day",
                )
            ),
            daily,
        ),
        vol.Optional(
            HOURLY_ENABLED, default=defaults[HOURLY_ENABLED]
        ): SensorSettingSelector(BooleanSelector()),
        vol.Optional(
            HOURLY_SCHEDULE, default=defaults[HOURLY_SCHEDULE]
        ): SensorSettingSelector(
            SelectSelector(
                SelectSelectorConfig(
                    options=["specific", "next", "interval"],
                    translation_key="hourly_schedule",
                )
            ),
            hourly,
        ),
        vol.Optional(
            HOURLY_HOURS, default=defaults[HOURLY_HOURS]
        ): SensorSettingSelector(
            SelectSelector(
                SelectSelectorConfig(
                    options=[str(hour) for hour in range(MAX_HOUR + 1)],
                    multiple=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            hourly,
            {"field": HOURLY_SCHEDULE, "value": "specific"},
        ),
        **dict(
            [
                number(HOURLY_COUNT, 1, "next"),
                number(HOURLY_START, 0, "interval"),
                number(HOURLY_END, 0, "interval"),
                number(HOURLY_INTERVAL, 1, "interval"),
            ]
        ),
    }


def apply_forecast_controls(values: dict) -> tuple[dict, dict[str, str]]:
    """Convert schedule selections into the existing runtime CSV fields."""
    values = dict(values)
    errors = {}
    # YAML imports that have not used the new form retain their existing offsets.
    if DAILY_ENABLED not in values and HOURLY_ENABLED not in values:
        return values, errors

    values = {**forecast_form_defaults(values), **values}

    days = sorted({int(day) for day in values[DAILY_DAYS]})
    hours = []
    if values[DAILY_ENABLED] and not days:
        errors[DAILY_DAYS] = "select_forecast_days"
    if values[HOURLY_ENABLED]:
        if values[HOURLY_SCHEDULE] == "specific":
            hours = sorted({int(hour) for hour in values[HOURLY_HOURS]})
            if not hours:
                errors[HOURLY_HOURS] = "select_forecast_hours"
        elif values[HOURLY_SCHEDULE] == "next":
            hours = list(range(1, values[HOURLY_COUNT] + 1))
        else:
            start, end = values[HOURLY_START], values[HOURLY_END]
            if start > end:
                errors[HOURLY_END] = "invalid_hourly_range"
            else:
                hours = list(range(start, end + 1, values[HOURLY_INTERVAL]))
    values[CONF_FORECAST] = ",".join(map(str, days)) if values[DAILY_ENABLED] else ""
    values[CONF_HOURLY_FORECAST] = ",".join(map(str, hours))
    return values, errors
