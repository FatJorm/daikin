#!/usr/bin/env python3

from yr.libyr import Yr

weather = Yr(location_name='Norge/Telemark/Skien/Skien')

wind_speed = dict()
wind_speed['data'] = [{'from': forecast['@from'], 'to': forecast['@to'], 'speed': float(forecast['windSpeed']['@mps'])} for forecast in weather.forecast()]
wind_speed['credit'] = weather.credit

print(wind_speed)
