"""Validation shared by numeric weather and sensor values."""

from math import isfinite


def valid_number(value) -> bool:
    """Return whether a measurement is finite and is not the missing sentinel."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value != -999
        and isfinite(value)
    )
