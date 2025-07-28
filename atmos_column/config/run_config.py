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
import yaml

class run_config_obj:
    '''The main configs object. Used to store all of the necessary config parameters take from an input_config.yaml type file'''

    def __init__(self,config_path = None, config_yaml_fname='input_config.yaml'):
        '''
        Args:
        config_yaml_fname (str) : name of the configuration file yaml. Should be in the same folder as this module, and default is input_config.yaml
        '''
        if config_path is None: #if the default is chosen
            config_path = os.path.dirname(__file__) #make the path the path where this was run, should be Atmos_Colum/atmos_column/config
        self.config_yaml_fullpath = os.path.join(config_path,config_yaml_fname) #save the config file path
        yaml_data = self.load_yaml() #load the yaml
        for key in yaml_data: #for all of the elements in the yaml
            setattr(self,key,yaml_data[key]) #set them as attributes in the class, to be accessed with self.key
        self.start_dt = self.dtstr_to_dttz(self.start_dt_str,self.timezone) #the yaml datetime is a string, so convert it to a datetime
        self.end_dt = self.dtstr_to_dttz(self.end_dt_str,self.timezone) #same for end datetime
        #self.folder_paths['hrrr_subset_path'] = os.path.join(self.folder_paths['hrrr_data_folder'],'subsets') #add the subset path for hrrr surface elevations
        #self.get_lat_lon_zasl() #get the lat/lon/zasl -- will be just the config if column type is not em27, if it is it will be taken from oof
        self.split_dt_ranges = self.get_split_dt_ranges() #split the datetimes into daily ranges
        self.adjust_met() #adjust the met data to the correct format for the run
        self.folder_paths['output_folder'] = os.path.join(self.folder_paths['Atmos_Column_folder'],'output') #set the output folder

    def adjust_met(self):
        '''Adjusts the met data to the correct format for the run'''
        if self.download_met == 'T':
            if self.folder_paths['met_folder'] == "stilt_parent":
                stilt_parent = os.path.split(self.folder_paths['stilt_folder'])[0]
                met_folder = os.path.join(stilt_parent,'met')
                if not os.path.exists(met_folder):
                    os.makedirs(met_folder)
                self.folder_paths['met_folder'] = met_folder
                self.run_stilt_configs['met_path'] = f"'{met_folder}'"
            elif not os.path.exists(self.folder_paths['met_folder']):
                raise ValueError('Error: met folder does not exist for the download and is not stilt_parent which can be automatically created')
        else:
            self.folder_paths['met_folder'] =  self.run_stilt_configs['met_path'][1:-1] #had to put the path in quotes for the R script, so remove them here
        
    def load_yaml(self):
        '''Loads the yaml from the yaml filepath'''
        with open(self.config_yaml_fullpath) as f:
            yaml_data = yaml.safe_load(f)
        return yaml_data

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
        if isinstance(dt_str, str):
            dt = datetime.datetime.strptime(dt_str,'%Y-%m-%d %H:%M:%S')
        elif isinstance(dt_str, datetime.datetime):
            dt = dt_str
        else:
            raise ValueError('Error: dt_str must be a string or datetime.datetime object')
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
    configs = run_config_obj(config_yaml_fname='input_config.yaml')
    print(configs.__dict__)

if __name__=='__main__':
    main()