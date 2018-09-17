#!/usr/bin/env python3

from yr.libyr import Yr

#weather = Yr(location_name="Italy/Trentino_and_South-Tirol/San_Michele_all'Adige")
weather = Yr(location_xyz=(11.13358, 46.19291, 210)) # xyz for Italy/Trentino_and_South-Tirol/San_Michele_all'Adige

for forecast in weather.forecast(as_json=True):
    print(forecast)
