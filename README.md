# Pirate Weather Integrations
This integration is designed to replace the default [Dark Sky](https://www.home-assistant.io/integrations/darksky/) integration in [Home Assistant](https://github.com/home-assistant/core/tree/dev/homeassistant/components/darksky) with a  modified and updated, but fully compatible version that relies on the [Pirate Weather API](https://pirateweather.net/) instead! 

To get a feel for the data returned by this API, check out <https://weather.pirateweather.net>! 

I'm really hoping to keep free access going for this API, but it does take money to run the AWS back-end. If you'd like to support this project, I have a sponsorship link setup on my [profile](https://github.com/sponsors/alexander0042/)! This project (especially the free tier) wouldn't be possibile without the ongoing support from the project sponsors, so they're the [heros](https://github.com/SJV83) [here](https://github.com/matthewj301)! 

[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/alexander0042)

<a href="https://www.buymeacoffee.com/pirateweather" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 30px !important;width: 130px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

While this integration is designed to be compatible with Dark Sky, the underlying code is significantly different. This version is designed to work with more modern versions of Home Assistant, and relies on asyncio, unified data update coordinators, and setup via the UI! A [legacy branch](https://github.com/alexander0042/pirate-weather-ha/tree/Legacy-Dark-Sky) that is a 1:1 replacement for the previous Dark Sky integration is also available, but is not recommended.


## Notices
While this integration is designed to be a drop in replacement for the Dark Sky integration, it is possible that small differences will occur. The underlying API should return similar results, but specific weather variables may be missing, and additional testing is needed to find and correct these edge cases. Please [document any issues](https://github.com/alexander0042/pirate-weather-ha/issues), and I can either update this integration or the weather API. 

The two most notable missing pieces at the moment are the language options and text summaries. Both of those are possible with the way I have things designed, but I need to write the code that generates the text, and then feed that into the Dark Sky translation module. For now, the text will display whatever the icon is showing, and it will always be in English.

## Why?
Since the Dark Sky API will be shutting down this year, I set out to write an alternative API that would return results with the identical syntax, allowing it to be used as a drop in replacement. This culminated in the [Pirate Weather API](https://pirateweather.net/), which is a series of AWS lambda functions that read, process, and serve NOAA weather forecasts in same style and syntax as the Dark Sky API did. 

This integration allows for any Home Assistant setup that uses Dark Sky to continue operating after it shuts down. While other weather integrations are available, this preserves anything that relies on unique aspects of Dark Sky (such as the minute-by-minute forecast) and let’s existing dashboards keep working. Plus, if you're interested in knowing exactly how your weather forecasts are generated, this is the "show me the numbers" approach, since the data returned is directly from NOAA, and every processing step I do is [documented](https://blog.pirateweather.net). If you're the sort of person who wants a [dense 34-page PowerPoint](http://rapidrefresh.noaa.gov/pdf/Alexander_AMS_NWP_2020.pdf) about why it rained when the forecast said it wouldn't, then this might be for you. 

## Documentation
Since this integration returns the same type of data as the default Dark Sky integration, the parameter documentation is the same as described at <https://www.home-assistant.io/integrations/weather.darksky> for the weather card and here: <https://www.home-assistant.io/integrations/darksky/> for the sensor.

# Installation
There are two methods to install this installation:

## HACS Installation (easiest)
1. Add `https://github.com/alexander0042/pirate-weather-ha` as a custom repository
2. Restart Home Assistant
3. Register for a Pirate Weather API Key here: <https://pirateweather.net/>
4. Log into the Pirate Weather API interface (<https://pirateweather.net/apis>), select `PirateForecast Beta`, and **click Subscribe**!
5. Add the Pirate Weather on the Integrations page of your Home Assistant Installation following the steps below.

## Manual Installation 
1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_component` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `pirateweather`.
4. Download _all_ the files from the `custom_components/pirateweather/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. Register for a Pirate Weather API Key here: <https://pirateweather.net/>
8. Log into the Pirate Weather API interface (<https://pirateweather.net/apis>), select `PirateForecast Beta`, and **click Subscribe**!
9. Add the Pirate Weather on the Integrations page of your Home Assistant Installation following the steps below.

## Configuration
The use to integration, click on the "Add Integration" button on the Integrations page in the Home Assistant Settings and search for Pirate Weather. This will open the add integration UI, shown below.

![Integration_Setup_A](Integration_Setup_A.png)

- The *API key* can be received from the [Pirate Weather Site](https://pirateweather.net/), and is only used to track usage and keep my AWS bills reasonable
- The *Integration Name* is what this weather source will be called. If you want to track the weather at multiple locations, change this. 
- The *Latitude* and *Longitude* for the forecast.
- Select if a *Weather Entity* and/or *Sensor Entity* is required. A Weather Entity creates the dashboard standard weather card, and can either provide a daily or hourly forecast. Selecting Sensor Entity will create separate sensors for each condition and forecast time. For example, a sensor for the temperature on day 0 (today), day 1, and day 2, for a total of three sensors. If unsure, start with leaving only the Weather Entity selected.

![Integration_Setup_B](Integration_Setup_B.png)

- The *Forecast Mode* for the Weather Entity, either forecasts every hour or every day.
- The language. At the moment, only English is supported.
- The days forecast sensors should be created for, in a csv list.
- The hours forecast sensors should be created for, in a csv list.
- The monitored conditions forecast sensors should be created for.
- If values should be rounded to the nearest integer.
- And which units the forecast sensors should be in. This integration works with the built-in Home Assistant units; however, this option allows rounding to be used.

### YAML Configuration
YAML configuration is still supported, but is depreciated and may be removed at some point in the future. If the integration detects an existing YAML integration, it will import and save it, allowing the yaml to be safely removed.

To use the integration via this approach, either add or edit to your `configuration.yaml` file with this block, using the new API key:

```yaml
weather:
  - platform: pirateweather
    api_key: <APIKEY>
    # Additional optional values:
    latitude: Location latitude
    longitude: Location longitude
    mode: "hourly" (default) or "daily"
    name: Custom name
    

# you can also get a sensor data
sensor:
  - platform: pirateweather
    api_key: <APIKEY>
    scan_interval: '00:15:00'
    monitored_conditions:
      - temperature
      - precip_probability
      - precip_type
      - humidity
      - cloud_cover
      - nearest_storm_distance
      - precip_intensity
      - wind_speed
```
