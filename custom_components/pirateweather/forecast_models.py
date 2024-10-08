"""Taken from the fantastic Dark Sky library: https://github.com/ZeevG/python-forecast.io in October 2024."""

import datetime
import requests


class UnicodeMixin:
    """Mixin class to handle defining the proper __str__ methods for Python 2 or 3 compatibility."""

    def __str__(self):
        """Returns the unicode representation of the object for Python 2/3 compatibility."""
        return self.__unicode__()


class PropertyUnavailable(AttributeError):
    """Exception raised when a requested property is unavailable in the forecast data."""


class Forecast(UnicodeMixin):
    """Represents the forecast data with utility methods to access various weather blocks."""

    def __init__(self, data, response, headers):
        """Initializes the Forecast with data, HTTP response, and headers."""
        self.response = response
        self.http_headers = headers
        self.json = data

        self._alerts = []
        for alertJSON in self.json.get("alerts", []):
            self._alerts.append(Alert(alertJSON))

    def update(self):
        """Updates the forecast data by making a new request to the same URL."""
        r = requests.get(self.response.url)
        self.json = r.json()
        self.response = r

    def currently(self):
        """Returns the current weather data block."""
        return self._forcastio_data("currently")

    def minutely(self):
        """Returns the minutely weather data block."""
        return self._forcastio_data("minutely")

    def hourly(self):
        """Returns the hourly weather data block."""
        return self._forcastio_data("hourly")

    def daily(self):
        """Returns the daily weather data block."""
        return self._forcastio_data("daily")

    def offset(self):
        """Returns the time zone offset for the forecast location."""
        return self.json["offset"]

    def alerts(self):
        """Returns the list of alerts issued for this forecast."""
        return self._alerts

    def _forcastio_data(self, key):
        """Helper method to retrieve specific weather data (currently, minutely, hourly, daily)."""
        keys = ["minutely", "currently", "hourly", "daily"]
        try:
            if key not in self.json:
                keys.remove(key)
                url = "{}&exclude={}{}".format(
                    self.response.url.split("&")[0],
                    ",".join(keys),
                    ",alerts,flags",
                )

                response = requests.get(url).json()
                self.json[key] = response[key]

            if key == "currently":
                return ForecastioDataPoint(self.json[key])
            return ForecastioDataBlock(self.json[key])
        except requests.HTTPError:
            if key == "currently":
                return ForecastioDataPoint()
            return ForecastioDataBlock()


class ForecastioDataBlock(UnicodeMixin):
    """Represents a block of weather data such as minutely, hourly, or daily summaries."""

    def __init__(self, d=None):
        """Initializes the data block with summary and icon information."""
        d = d or {}
        self.summary = d.get("summary")
        self.icon = d.get("icon")
        self.data = [ForecastioDataPoint(datapoint) for datapoint in d.get("data", [])]

    def __unicode__(self):
        """Returns a string representation of the data block."""
        return "<ForecastioDataBlock instance: " "%s with %d ForecastioDataPoints>" % (
            self.summary,
            len(self.data),
        )


class ForecastioDataPoint(UnicodeMixin):
    """Represents a single data point in a weather forecast, such as an hourly or daily data point."""

    def __init__(self, d={}):
        """Initializes the data point with timestamp and weather information."""
        self.d = d

        try:
            self.time = datetime.datetime.fromtimestamp(int(d["time"]))
            self.utime = d["time"]
        except KeyError:
            pass

        try:
            sr_time = int(d["sunriseTime"])
            self.sunriseTime = datetime.datetime.fromtimestamp(sr_time)
        except KeyError:
            self.sunriseTime = None

        try:
            ss_time = int(d["sunsetTime"])
            self.sunsetTime = datetime.datetime.fromtimestamp(ss_time)
        except KeyError:
            self.sunsetTime = None

    def __getattr__(self, name):
        """Allows access to weather properties dynamically, raising an error if unavailable."""
        try:
            return self.d[name]
        except KeyError as err:
            raise PropertyUnavailable(
                f"Property '{name}' is not valid"
                " or is not available for this forecast"
            ) from err

    def __unicode__(self):
        """Returns a string representation of the data point."""
        return "<ForecastioDataPoint instance: " f"{self.summary} at {self.time}>"


class Alert(UnicodeMixin):
    """Represents a weather alert, such as a storm warning or flood alert."""

    def __init__(self, json):
        """Initializes the alert with the raw JSON data."""
        self.json = json

    def __getattr__(self, name):
        """Allows access to alert properties dynamically, raising an error if unavailable."""
        try:
            return self.json[name]
        except KeyError as err:
            raise PropertyUnavailable(
                f"Property '{name}' is not valid"
                " or is not available for this alert"
            ) from err

    def __unicode__(self):
        """Returns a string representation of the alert."""
        return f"<Alert instance: {self.title} at {self.time}>"
