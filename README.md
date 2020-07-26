# Strava activities exploration

This repository contains modules and Jupyter notebooks with code for downloading Strava activities
data and analyze it in interactive maps like [kepler.gl](https://kepler.gl/) and [folium](https://python-visualization.github.io/folium/)

Now it can download all activities from selected clubs. See [configuration](#configuration)

# Demo

![Demo animation](demo-files/stravaweb-demo.gif)

- [Nizhny Novgorod rides 24-26 July](https://reclosedev.github.io/stravaweb/nn_2020-07-24-26.html)
- [All routes from Nizhny Novgorod clubs 26 July (from 14 June)](https://reclosedev.github.io/stravaweb/all-from-nn-2020-06-14-2020-07-26.html)


# Installation
[Poetry](https://python-poetry.org/) is used for this project
```bash
$ poetry install
```

It's not ready-to-use tool. Use it as basis for your own research.

# Configuration

[YAML](https://yaml.org) is used for configuration. See [config.yaml.example](etc/config.yaml.example)

# Notes about data downloading
Strava API is very limited in terms of downloading others activities. So [stravaweb](stravaweb) 
client uses HTML API. 
Strava limits downloads of activity data, approximately 40 downloads allowed in short period, 
so this code can use multiple accounts.
