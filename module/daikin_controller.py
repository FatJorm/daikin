# -*- coding: utf-8 -*-

import os
import sys
import time
import json
from datetime import datetime as dt
from module.daikin_aircon import *
from yr.libyr import Yr
from module.python_sectoralarm_master.sectoralarm.session import Session
import pickle
from collections import deque
from math import floor
import pandas as pd

os.chdir(sys.path[0])

PANDA_FRAME = 'panda_frame'
INDOOR_TEMP = 'indoor_temp_l'
MOMPOW = 'mompow_l'
LOG = 'log.txt' 

class Daikin_Controller(object):
    def __init__(self, ip):
        self.number_of_hours = 6
        self.time = self.get_time_now()
        self.aircon = Aircon(ip)
        self.control_info = self.aircon.get_control_info()
        self.sensor_info = self.aircon.get_sensor_info()
        self.mompow = (int(self.sensor_info['mompow'])) 
        self.yr_weather_l = self.get_yr_weather_l()
        self.yr_future_low_temp = self.get_yr_future_low_temp()
        self.yr_outdoor_temp = self.get_yr_outdoor_temp()
        self.daikin_indoor_temp = self.aircon.get_indoor_temp()
        self.kitchen_temp = self.get_kitchen_temp()
        self.daikin_outdoor_temp = self.aircon.get_outdoor_temp()
        self.daikin_target_indoor_temp = self.control_info['stemp']
        self.target_temp = self.get_target_temp()
               
   
    def set_mode_heating(self):
      aircon_mode = self.control_info['mode']
      if aircon_mode != 4:
          self.aircon.set_control_info({'mode':4 })

    def set_mode_cooling(self):
        aircon_mode = self.control_info['mode']
        if aircon_mode != 3:
            self.aircon.set_control_info({'mode':3})
    
    def set_temp(self):
        if not (self.target_temp == self.daikin_target_indoor_temp):
            self.aircon.set_target_temp(self.target_temp)

    def get_time_now(self):
        return dt.now()
        
    def update_panda_frame(self):
        panda = self.load_obj(self.panda_pickel_file)
        time_stamp = datetime.datetime.strftime(datetimme.datetime.nowi())

    def get_yr_weather_l(self):
        weather = Yr(location_name='Sverige/Västra_Götaland/Lerum', forecast_link='forecast_hour_by_hour')
        weather_l = [f for f in weather.forecast()]
        return weather_l

    def get_yr_outdoor_temp(self):
        return int(self.yr_weather_l[0]['temperature']['@value'])
 
    def get_yr_future_low_temp(self):
        temp_l = [int(self.yr_weather_l[i]['temperature']['@value']) for i in range(self.number_of_hours)]
        temp_low = 30
        for temp in temp_l:
            if temp < temp_low:
                temp_low = temp
        return temp_low

    def update_log(self):
        log_path = os.path.join(os.getcwd(),LOG)
        with open(log_path, 'a+') as f:
            f.write(str(self))

    def get_update_panda_frame(self):
        panda_frame_d = {}
        panda_frame_d['Time'] = [self.time]
        panda_frame_d['Daikin Outdoor Temp'] = [self.daikin_outdoor_temp]
        panda_frame_d['Daikin Indoor Temp'] = [self.daikin_indoor_temp]
        panda_frame_d['Sector Kitchen Temp'] = [self.kitchen_temp]
        panda_frame_d['Daikin Target Indoor Temp'] = [self.daikin_target_indoor_temp]
        panda_frame_d['Yr Outdoor Temp'] = [self.yr_outdoor_temp]
        panda_frame_d['Yr Future Low Outdoor Temp'] = [self.yr_future_low_temp]
        panda_frame_d['Target Indoor Temp'] = [self.target_temp]
        panda_frame_d['mompow'] = self.mompow
        panda_frame_d['number_of_hours'] = self.number_of_hours
        panda_df_update = pd.DataFrame.from_dict(panda_frame_d).set_index('Time')
        return panda_df_update

    def update_panda_frame(self):
        panda_df = self.load_panda_from_pickel()
        panda_df_update = self.get_update_panda_frame()
        frame = panda_df.append(panda_df_update)
        self.save_panda_to_pickel(frame)
        
    def load_panda_from_pickel(self):
        try:
            panda_df = self.load_obj(PANDA_FRAME)
        except:
            panda_df = pd.DataFrame()
        return panda_df

    def save_panda_to_pickel(self, frame):
        self.save_obj(frame,PANDA_FRAME)

    def get_kitchen_temp(self):
        with open('/home/pi/Python/passwd/sector.pickle', 'rb') as f:
            s = pickle.load(f)
        mail = s['user']
        passwd = s['passwd']
        number = s['nr']
        sector = Session(mail, passwd, number)
        device_list = sector.get_temperature()['temperatureComponentList']
        firealarm_kitchen = device_list[0]
        firealarm_upstairs = device_list[1]
        ir_sensor_bedroom = device_list[2]
        return int(firealarm_kitchen['temperature'])

    def get_target_temp(self):
        outdoor_temp = self.yr_future_low_temp
        if outdoor_temp < 0:
            target = 26.0
            self.number_of_hours = 6
        elif outdoor_temp < 2:
            target = 24.0
            self.number_of_hours = 6
        elif outdoor_temp < 4:
            target = 22.0
            self.number_of_hours = 6
        elif outdoor_temp < 10:
            target = 21.0
            self.number_of_hours = 4
        elif outdoor_temp < 15:
            target = 20.0
            self.number_of_hours = 2
        else:
            target = 18.0
            self.number_of_hours = 1
        return self.apply_kitchen_sensor_value(target)

    def apply_kitchen_sensor_value(self, target):
        if self.kitchen_temp > 24 and self.yr_outdoor_temp > 24:
            self.set_mode_cooling()
            return(22.0)
        else:
            self.set_mode_heating()
            if (target < self.daikin_target_indoor_temp) and (self.kitchen_temp > 22):
                return target
            elif (target > self.daikin_target_indoor_temp) and (self.kitchen_temp <= 22):
                return target
            else:
                return self.daikin_target_indoor_temp
       
    def boost_mode(self):
        indoor_temp = self.get_low_indoor_temp(7)
        return indoor_temp + 2

    def get_low_indoor_temp(self, samples):
        collection = self.load_indoor_temp_collection(samples)
        collection.append(self.daikin_indoor_temp)
        self.save_indoor_temp_collection(collection)
        return self.indoor_temp_median_hour(collection)

    def load_indoor_temp_collection(self,samples):
        try:
            indoor_temp = self.load_obj(INDOOR_TEMP)
            if indoor_temp.maxlen != samples:
                indoor_temp = deque(list(indoor_temp),maxlen=samples)
        except:
            indoor_temp = deque([25,25,25],maxlen=samples)
        return indoor_temp

    def save_indoor_temp_collection(self,collection):
        self.save_obj(collection,INDOOR_TEMP)    

    def save_obj(self,obj,name):
        path = os.path.join(os.getcwd(), 'module/obj/'+name+'.pkl')
        if not os.path.exists(path):
            open(path,'w+')
        with open(path,'wb') as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

    def load_obj(self,name):
        path = os.path.join(os.getcwd(), 'module/obj/'+name+'.pkl')
        with open(path,'rb') as f:
            return pickle.load(f)

    def indoor_temp_median_hour(self,collection):
        s = 30
        l=list(collection)
        while(len(l)>2):
            l = self.remove_extreme_values(l)
        return sum(l)/len(l)
    
    
    def remove_max(self, collection):
        l = sorted(collection)
        del(l[-1])
        return l

    def remove_min(self, collection):
        l = sorted(collection, reverse=True)
        del(l[-1])
        return l

    def remove_extreme_values(self, collection):
        l = self.remove_max(collection)
        l = self.remove_min(l)
        return l

    def __str__(self):
        return '{0} Daikin Outdoor Temp: {1}, Daikin Indoor Temp: {2}, Daikin Target Indoor Temp: {3}, Yr Outdoor Temp: {4}, Yr Lowest Outdoor Temp in {5} Hours: {6}, Target Indoor Temp: {7}, MomPow: {8}, Kitchen Temp: {9}\n'.format(dt.strftime(self.time,'%Y-%m-%d %H:%M:%S'), self.daikin_outdoor_temp, self.daikin_indoor_temp, self.daikin_target_indoor_temp, self.yr_outdoor_temp, self.number_of_hours, self.yr_future_low_temp,self.target_temp, self.mompow, self.kitchen_temp)

if __name__=='__main__':
    a = Daikin_Controller('192.168.1.168')
    print(a)   
