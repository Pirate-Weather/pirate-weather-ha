"""Taken from the fantastic Dark Sky library: https://github.com/ZeevG/python-forecast.io in Octovber 2024."""

import datetime

import requests


class UnicodeMixin:
    """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

    def __str__(self):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""
        return self.__unicode__()


class PropertyUnavailable(AttributeError):
    """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""


class Forecast(UnicodeMixin):
    """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

    def __init__(self, data, response, headers):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        self.response = response
        self.http_headers = headers
        self.json = data

        self._alerts = []
        for alertJSON in self.json.get("alerts", []):
            self._alerts.append(Alert(alertJSON))

    def update(self):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        r = requests.get(self.response.url)
        self.json = r.json()
        self.response = r

    def currently(self):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        return self._forcastio_data("currently")

    def minutely(self):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        return self._forcastio_data("minutely")

    def hourly(self):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        return self._forcastio_data("hourly")

    def daily(self):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        return self._forcastio_data("daily")

    def offset(self):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        return self.json["offset"]

    def alerts(self):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        return self._alerts

    def _forcastio_data(self, key):
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
    """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

    def __init__(self, d=None):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        d = d or {}
        self.summary = d.get("summary")
        self.icon = d.get("icon")

        self.data = [ForecastioDataPoint(datapoint) for datapoint in d.get("data", [])]

    def __unicode__(self):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        return "<ForecastioDataBlock instance: " "%s with %d ForecastioDataPoints>" % (
            self.summary,
            len(self.data),
        )


class ForecastioDataPoint(UnicodeMixin):
    """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

    def __init__(self, d={}):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

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
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        try:
            return self.d[name]
        except KeyError as err:
            raise PropertyUnavailable(
                f"Property '{name}' is not valid"
                " or is not available for this forecast"
            ) from err

    def __unicode__(self):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        return "<ForecastioDataPoint instance: " f"{self.summary} at {self.time}>"


class Alert(UnicodeMixin):
    """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

    def __init__(self, json):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        self.json = json

    def __getattr__(self, name):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        try:
            return self.json[name]
        except KeyError as err:
            raise PropertyUnavailable(
                f"Property '{name}' is not valid"
                " or is not available for this forecast"
            ) from err

    def __unicode__(self):
        """Mixin class to handle defining the proper __str__/__unicode__ methods in Python 2 or 3."""

        return f"<Alert instance: {self.title} at {self.time}>"
