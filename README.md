# Pirate Weather Integrations
This integration is designed to replace the defunct Dark Sky integration in Home Assistant with a modified and updated, but fully compatible version that relies on the [Pirate Weather API](https://pirateweather.net/en/latest/) instead!

To get a feel for the data returned by this API, check out <https://merrysky.net>! To view the current API status check out the [status page](https://pirateweather.xitoring.io/).

Configuration now includes an optional field to exclude specific weather models from the forecast.

I'm really hoping to keep free access going for this API, but it does take money to run the AWS back-end. If you'd like to support this project, I have a sponsorship link setup on my [profile](https://github.com/sponsors/alexander0042/)! This project (especially the free tier) wouldn't be possibile without the ongoing support from the project sponsors, so they're the [heros](https://github.com/SJV83) [here](https://github.com/matthewj301)! 

[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/alexander0042)

<a href="https://www.buymeacoffee.com/pirateweather" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 30px !important;width: 130px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

If you get an `AttributeError: PRECIPITATION` upon importing the integration please check that you are running HA 2022.10 or later. If you are running an earlier version please try updating your HA install and try the import again. If you are unable to update your version of HA then you can use the [legacy branch](https://github.com/alexander0042/pirate-weather-ha/tree/Legacy-Dark-Sky) instead.

## Notices
While this integration is designed to be compatible with Dark Sky, the underlying code is significantly different. This version is designed to work with more modern versions of Home Assistant, and relies on asyncio, unified data update coordinators, and setup via the UI! A [legacy branch](https://github.com/alexander0042/pirate-weather-ha/tree/Legacy-Dark-Sky) that is a 1:1 replacement for the previous Dark Sky integration is also available, but is not recommended.

The underlying API should return similar results, but specific weather variables may be missing, and additional testing is needed to find and correct these edge cases. Please [document any issues](https://github.com/alexander0042/pirate-weather-ha/issues), and I can either update this integration or the weather API. 

The two most notable missing pieces at the moment are the language options and text summaries. Both of those are possible with the way I have things designed, but I need to write the code that generates the text, and then feed that into the Dark Sky translation module. For now, the text will display whatever the icon is showing, and it will always be in English.

## Why?
Since the Dark Sky API has shut down, I set out to write an alternative API that would return results with the identical syntax, allowing it to be used as a drop in replacement. This culminated in the [Pirate Weather API](https://pirateweather.net/en/latest/), which is a series of AWS lambda functions that read, process, and serve NOAA weather forecasts in same style and syntax as the Dark Sky API did. 

This integration allows for any Home Assistant setup that uses Dark Sky to continue operating after it shuts down. While other weather integrations are available, this preserves anything that relies on unique aspects of Dark Sky (such as the minute-by-minute forecast) and let’s existing dashboards keep working. Plus, if you're interested in knowing exactly how your weather forecasts are generated, this is the "show me the numbers" approach, since the data returned is directly from NOAA, and every processing step I do is [documented](https://pirateweather.net/en/latest/Blog/InfrastructureOverview/). If you're the sort of person who wants a [dense 34-page PowerPoint](http://rapidrefresh.noaa.gov/pdf/Alexander_AMS_NWP_2020.pdf) about why it rained when the forecast said it wouldn't, then this might be for you. 

## Documentation
Since this integration returns the same type of data as the default Dark Sky integration, the parameter documentation is the same as described at <https://web.archive.org/web/20230128172320/https://www.home-assistant.io/integrations/weather.darksky/> for the weather card and here: <https://web.archive.org/web/20230326100953/https://www.home-assistant.io/integrations/darksky> for the sensor.

To view the full integration documentation and installation instructions visit [https://pirateweather.net/en/latest/ha/](https://pirateweather.net/en/latest/ha/).
