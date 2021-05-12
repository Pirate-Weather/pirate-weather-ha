# Pirate Weather Integrations

This integration is designed to replace the default [Dark Sky](https://www.home-assistant.io/integrations/darksky/) integration in [Home Assistant](https://github.com/home-assistant/core/tree/dev/homeassistant/components/darksky) with a slightly modified, but fully compatable version that relies on the [Pirate Weather API](https://pirateweather.net/) instead! 

## Notices

This integration will take priority over the built in Dark Sky integration. While it is deigned to be a drop in replacement, it is possibile that small differences will occur. The underlying API shoudld return similar results, but specific weather variables may be missing, and additional testing is needed to find and correct these edge cases. Please [document any issues](https://github.com/alexander0042/pirate-weather-hacs/issues), and I can either update this integration or the weather API. 

The two most notable missing pieces at the moment are the language options and text summaries. Both of those are possibile with the way I have things designed, but I need to write the code that generates the text, and then feed that into the Dark Sky translation module. For now, the text will display whatever the icon is showing, and it will always be in English.

## Why?

Since the Dark Sky API will be shutting down this year, I set out to write an altarnative API that would return results with the identical syntax, allowing it to be used as a drop in replacement. This culminated in the [Pirate Weather API](https://pirateweather.net/), which is a series of AWS lambda functions that read, process, and serve NOAA weather forecasts in same style and syntax as the Dark Sky API did. 

This integration allows for any Home Assistant setup that uses Dark Sky to continue operating after it shuts down. While other weather integrations are availible, this preserves anything that relies on unique aspects of Dark Sky (such as the minute-by-minute forecast) and lets existing dashboards keep working. Plus, if you're interested in knowing exactly how your weather forecasts are generated, this is the "show me the numbers" approach, since the data returned is directly from NOAA, and every processing step I do is [documented](blog.pirateweather.net). If you're the sort of person who wants a [dense 34 page PowerPoint](http://rapidrefresh.noaa.gov/pdf/Alexander_AMS_NWP_2020.pdf) about why it rained when the forecast said it wouldn't, then this might be for you. 

## What it does

This integration adds creates custom `sensor.py` and `weather.py` files to change their data source from Dark Sky to Pirate Weather. Specifically, these functions are built around the [forecast.io python package](https://pypi.org/project/python-forecastio/), and so instead of calling `forecastio.load_forecast`, they call `forecastio.manual`, which allows for a different API URL to be used. 

The only other change is to call the API every 15 minutes instead of every 3. I only just graduated, so trying to keep my AWS bill reasonable here. If you need a more frequent update interval, or would like to support this project, I've set up a donation link!  

<a href="https://www.buymeacoffee.com/pirateweather" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

## Documentation

Since this integration returns the same type of data as the defauly Dark Sky integration, the paramater documentation is the same as described here: <https://www.home-assistant.io/integrations/darksky/>.


## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `darksky`.
4. Download _all_ the files from the `custom_components/darksky/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. Register for a Pirate Weather API Key here: <https://pirateweather.net/>
8. Log into the Pirate Weather API interface (<https://pirateweather.net/apis>), select `PirateForecas Beta`, and **click Subscribe**!

Edit your `configuration.yaml` file with:

`weather:`
`  - platform: darksky`
`    api_key: <APIKEY>`