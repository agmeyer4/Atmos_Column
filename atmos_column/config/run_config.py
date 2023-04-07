import numpy as np
from .input_config import *
import datetime
import pytz
import os

class run_config_obj:
    def __init__(self):
        self.column_type = column_type
        self.interval = interval
        self.data_filter = data_filter
        self.start_dt = self.dtstr_to_dttz(start_dt_str,timezone)
        self.end_dt = self.dtstr_to_dttz(end_dt_str,timezone)
        self.timezone = timezone
        self.folder_paths = folder_paths
        self.folder_paths['hrrr_subset_path'] = os.path.join(folder_paths['hrrr_data_folder'],'subsets')
        self.hrrr_subset_datestr=hrrr_subset_datestr
        self.z_ail_list = z_ail_list
        self.inst_lat,self.inst_lon,self.inst_zasl = self.get_lat_lon_zasl()
        self.split_dt_ranges = self.get_split_dt_ranges()

    def get_lat_lon_zasl(self):
        if self.column_type == 'em27':
            self.inst_lat=self.inst_lon=self.inst_zasl=np.nan
        else:
            self.inst_lat = inst_lat
            self.inst_lon = inst_lon
            self.inst_zasl = inst_zasl 
        return inst_lat,inst_lon,inst_zasl

    def dtstr_to_dttz(self,dt_str,timezone):
        dt = datetime.datetime.strptime(dt_str,'%Y-%m-%d %H:%M:%S')
        dt = pytz.timezone(timezone).localize(dt)
        return dt

    def get_split_dt_ranges(self):
        if self.start_dt > self.end_dt:
            raise ValueError('Error: input config datetimes are incorrect - end datetime is before start datetime')
        split_dt_list = [] #initialize the day strings in the range
        if self.start_dt.date() == self.end_dt.date():
            split_dt_list.append({'dt1':self.start_dt,'dt2':self.end_dt})
            return split_dt_list
        
        delta_days = self.end_dt.date()-self.start_dt.date() #get the number of days delta between the end and the start
        for i in range(delta_days.days +1): #loop through that number of days 
            date = self.start_dt.date() + datetime.timedelta(days=i) #get the day by incrementing by i (how many days past the start)
            if date == self.start_dt.date():
                dt1 = self.start_dt
                dt2 = pytz.timezone(self.timezone).localize(datetime.datetime(date.year,date.month,date.day,23,59,59))
            elif date == self.end_dt.date():
                dt1 = pytz.timezone(self.timezone).localize(datetime.datetime(date.year,date.month,date.day,0,0,0,))
                dt2 = self.end_dt
            else:
                dt1 = pytz.timezone(self.timezone).localize(datetime.datetime(date.year,date.month,date.day,0,0,0,))
                dt2 = pytz.timezone(self.timezone).localize(datetime.datetime(date.year,date.month,date.day,23,59,59))
            split_dt_list.append({'dt1':dt1,'dt2':dt2})
        return split_dt_list

def main():
    configs = run_config_obj()
    print(configs.__dict__)

if __name__=='__main__':
    main()