import numpy as np
import datetime
import pytz
import os
import json
import multiprocessing

class run_config_obj:
    def __init__(self,config_json_fname='input_config.json'):
        self.config_json_fullpath = os.path.join(os.path.dirname(__file__),config_json_fname)
        json_data = self.load_json()
        for key in json_data:
            setattr(self,key,json_data[key])
        self.start_dt = self.dtstr_to_dttz(self.start_dt_str,self.timezone)
        self.end_dt = self.dtstr_to_dttz(self.end_dt_str,self.timezone)
        self.folder_paths['hrrr_subset_path'] = os.path.join(self.folder_paths['hrrr_data_folder'],'subsets')
        self.get_lat_lon_zasl()
        self.split_dt_ranges = self.get_split_dt_ranges()
        self.run_stilt_configs['n_hours'] = self.backtraj_hours
        self.get_cores()

    def get_cores(self):
        avail_cores = multiprocessing.cpu_count()
        if self.cores == 'max':
            self.cores = avail_cores
        if self.cores > avail_cores:
            raise ValueError('Error in input config: more cores than are available')


    def load_json(self):
        with open(self.config_json_fullpath) as f:
            json_data = json.load(f)
        return json_data

    def get_lat_lon_zasl(self):
        if self.column_type == 'em27':
            self.inst_lat=self.inst_lon=self.inst_zasl=np.nan

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
    configs = run_config_obj('/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Atmos_Column/atmos_column/config/input_config.json')
    print(configs.__dict__)

if __name__=='__main__':
    main()