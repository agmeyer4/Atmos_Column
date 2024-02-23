'''
Module: run_config.py
Author: Aaron G. Meyer (agmeyer4@gmail.com)
Description: 
This module is used to load and configure the configs jsons in the same folder. See input_config_description.txt for more information
about what the input_config.json type files contain and how to edit. 
'''

#Imports
import numpy as np
import datetime
import pytz
import os
import json
import multiprocessing

class run_config_obj:
    '''The main configs object. Used to store all of the necessary config parameters take from an input_config.json type file'''

    def __init__(self,config_json_fname='input_config.json'):
        '''
        Args:
        config_json_fname (str) : name of the configuration file json. Should be in the same folder as this module, and default is input_config.json
        '''
        self.config_json_fullpath = os.path.join(os.path.dirname(__file__),config_json_fname) #save the config file path
        json_data = self.load_json() #load the json
        for key in json_data: #for all of the elements in the json
            setattr(self,key,json_data[key]) #set them as attributes in the class, to be accessed with self.key
        self.start_dt = self.dtstr_to_dttz(self.start_dt_str,self.timezone) #the json datetime is a string, so convert it to a datetime
        self.end_dt = self.dtstr_to_dttz(self.end_dt_str,self.timezone) #same for end datetime
        #self.folder_paths['hrrr_subset_path'] = os.path.join(self.folder_paths['hrrr_data_folder'],'subsets') #add the subset path for hrrr surface elevations
        self.get_lat_lon_zasl() #get the lat/lon/zasl -- will be just the config if column type is not em27, if it is it will be taken from oof
        self.split_dt_ranges = self.get_split_dt_ranges() #split the datetimes into daily ranges
        self.run_stilt_configs['n_hours'] = self.backtraj_hours #add the n_hours parameter to the run stilt cnofigs parameter dict
    #     self.get_cores() #get the number of cores to use

    # def get_cores(self):
    #     '''Gets the number of cores to use from the config file'''

    #     avail_cores = multiprocessing.cpu_count() #find out how many cores are available
    #     if self.cores == 'max': #if the cores parameter is set to "max"
    #         self.cores = avail_cores #reset it to the number of cores available
    #     if self.cores > avail_cores: #cant use more cores than we have!
    #         raise ValueError('Error in input config: more cores than are available')

    def load_json(self):
        '''Loads the json from the json filepath'''

        with open(self.config_json_fullpath) as f:
            json_data = json.load(f)
        return json_data

    def get_lat_lon_zasl(self):
        '''Sets the lat/lon/zasl to nan if the column type is em27. These values will then be set later in create_receptors to avoid confusion'''

        if self.column_type == 'em27':
            self.inst_lat=self.inst_lon=self.inst_zasl=np.nan

    def dtstr_to_dttz(self,dt_str,timezone):
        '''Converts a datetime string and timezone to a tz-aware datetime.datetime
        
        Args:
        dt_str (str) : string of form YYYY-mm-dd HH:MM:SS
        timezone (str) : string representing the timezone to use (ex UTC)
        
        Returns:
        dt (datetime.datetime) : tz-aware datetime.datetime object corresponding to the inputs
        '''

        dt = datetime.datetime.strptime(dt_str,'%Y-%m-%d %H:%M:%S')
        dt = pytz.timezone(timezone).localize(dt)
        return dt

    def get_split_dt_ranges(self):
        '''Splits the input datetime range into daily ranges'''

        if self.start_dt > self.end_dt: #make sure start is before end
            raise ValueError('Error: input config datetimes are incorrect - end datetime is before start datetime')
        split_dt_list = [] #initialize the day strings in the range
        if self.start_dt.date() == self.end_dt.date(): #if start and end are the same date
            split_dt_list.append({'dt1':self.start_dt,'dt2':self.end_dt}) #there's only one range, from start to end, so use and return that
            return split_dt_list
        
        delta_days = self.end_dt.date()-self.start_dt.date() #get the number of days delta between the end and the start
        for i in range(delta_days.days +1): #loop through that number of days 
            date = self.start_dt.date() + datetime.timedelta(days=i) #get the day by incrementing by i (how many days past the start)
            if date == self.start_dt.date(): #if we're in the first day
                dt1 = self.start_dt #start with the start datetime
                dt2 = pytz.timezone(self.timezone).localize(datetime.datetime(date.year,date.month,date.day,23,59,59)) #and end with the last second of the day
            elif date == self.end_dt.date(): #if we're in the last day
                dt1 = pytz.timezone(self.timezone).localize(datetime.datetime(date.year,date.month,date.day,0,0,0,)) #start with the first second of the day
                dt2 = self.end_dt #and end with the end datetime
            else:#if we're in a full middle day
                dt1 = pytz.timezone(self.timezone).localize(datetime.datetime(date.year,date.month,date.day,0,0,0,)) #start with the first second
                dt2 = pytz.timezone(self.timezone).localize(datetime.datetime(date.year,date.month,date.day,23,59,59)) #and end with the last one
            split_dt_list.append({'dt1':dt1,'dt2':dt2}) #append the range to the list
        return split_dt_list

def main():
    configs = run_config_obj('input_config.json')
    print(configs.__dict__)

if __name__=='__main__':
    main()