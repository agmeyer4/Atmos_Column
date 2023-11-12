'''
Module: create_receptors.py
Author: Aaron G. Meyer (agmeyer4@gmail.com)
Description: 
This module is used to create total column receptors for STILT runs. These receptors represent points on the column from which to 
release particles as a way to discretize an integrated column measurment for Lagrangian transport modeling (STILT). 

Typically, the functions and classes in this module will be used in "full_run.py". However, this module can function as a standalone
method for creating receptor files based on the type of data you want. 

To use in standalone mode, note that running <python create_receptors.py> will grab configuration settings from the input_config file defined in main()
All parameter can be changed in the input config and the result of running <python create_receptors.py> will be the creation of receptor
files in output/receptors. See main() for detailed code description. 
'''

#Import
import os
from funcs import ac_funcs as ac
from config import run_config, structure_check
import datetime

class receptor_creator:
    '''
    A class used to creat receptors based on input configurations
    '''

    def __init__(self,configs,dt1,dt2):
        '''
        Args:
        configs (obj, from config/run_config.run_config_obj()) : configuration parameters scraped from the input config file
        dt1 (datetime.datetime) : beginning datetime
        dt2 (datetime.datetime) : ending datetime 
        '''
        self.configs = configs
        self.dt1 = dt1
        self.dt2 = dt2
    
    def create_receptors(self):
        '''
        Creates the receptors and saves them to the correct output/receptors folder based on column type and other configs
        TODO: Add more types of receptor creators (methaneAIR, satellites, etc)        
        '''

        print(f"Creating receptors and saving to {self.configs.folder_paths['output_folder']}")
        if self.configs.column_type == 'ground':
            self.ground_rec_creator()
        elif self.configs.column_type == 'em27':
            self.em27_rec_creator()
        else:
            raise Exception(f'Config column type = {self.configs.column_type} not recognized. Try a recognizable config.')

    def em27_rec_creator(self):
        '''Create and store a receptor file for STILT using EM27 data to define certain parameters
        
        Most importantly, this method will overwrite the lat/lon/zasl in the configs file using the data directly from
        the em27 oof files. This method will also clip days to the length of the oof data, rather than running all hours
        when the sun is up. 
        '''

        print(f'Column type is "em27". Slant columns will be created for datetimes with existing oof files')
        print(f'Instrument lat/lon/zasl will be taken from oof files')
        print(f"Creating receptors for {len(self.configs.split_dt_ranges)} dates in range.")

        my_oof_manager = ac.oof_manager(self.configs.folder_paths['column_data_folder'],self.configs.timezone) #create the oof manager
        oof_df = my_oof_manager.load_oof_df_inrange(self.dt1,self.dt2) #load the oof data in the required range
        if len(oof_df) == 0: #if there isn't any oof data in that range
            print(f'No oof data for {self.dt1} to {self.dt2}') #tell us
            return #and just return nothing 
        inst_lat,inst_lon,inst_zasl = my_oof_manager.check_get_loc(oof_df) #grab the instrument lat/lon/zasl from the oof dataframe and check to make sure it's the same
        gsh = ac.ground_slant_handler(inst_lat,
                                      inst_lon,
                                      inst_zasl,
                                      self.configs.z_ail_list) #create the slant handler   
        self.configs.inst_lat,self.configs.inst_lon,self.configs.inst_zasl = inst_lat,inst_lon,inst_zasl #add the inst location taken from oof to the config object
        #Run from the interval before the start and after the end of the oof dataframe, rather than the whole day (clip to oof data)   
        dt1_oof = oof_df.index[0].floor(self.configs.interval)  #floor is rounding down to the nearest interval
        dt2_oof = oof_df.index[-1].ceil(self.configs.interval) #ceil is rounding up to the nearest interval
        if dt2_oof > self.dt2: #we don't want to go past dt2
            dt2_oof = self.dt2 #so set it equal if the last dt in the oof file is bigger -- this happens when it runs past midnight often
        my_dem_handler = ac.DEM_handler(self.configs.folder_paths['dem_folder'],
                                self.configs.dem_fname,
                                self.configs.dem_typeid)
        slant_df = gsh.run_slant_at_intervals(dt1_oof,dt2_oof,my_dem_handler) #Get the slant column between the oof datetimes
        receptor_df = ac.slant_df_to_rec_df(slant_df) #transform it to a receptor dataframe style
        receptor_path = os.path.join(self.configs.folder_paths['output_folder'],'receptors',self.configs.column_type) #get the path, including the column type, where receptor csv will be stored
        fname = self.get_rec_fname() #get the filename of the receptor
        receptor_fullpath = os.path.join(receptor_path,fname) #join the full path
        self.receptor_header(receptor_fullpath,dt1_oof,dt2_oof) #write the receptor header
        receptor_df.to_csv(receptor_fullpath,mode = 'a',index=False) #append the receptor dataframe to the created receptor csv with header. 

    def ground_rec_creator(self):
        '''Create and store a receptor file for STILT using a generic "ground" slant column with interval
        
        This method will use all of the parameters in the input_configs, and has nothing to do with oof files or em27 data. 
        '''

        print(f'Column type is generic "ground"')
        print(f'Instrument lat/lon/zasl taken from configs file')
        print(f"Creating receptors for {len(self.configs.split_dt_ranges)} dates in range.")
        print(self.configs.inst_lat)
        gsh = ac.ground_slant_handler(self.configs.inst_lat,
                                    self.configs.inst_lon,
                                    self.configs.inst_zasl,
                                    self.configs.z_ail_list) #create the slant handler
        my_dem_handler = ac.DEM_handler(self.configs.folder_paths['dem_folder'],
                                        self.configs.dem_fname,
                                        self.configs.dem_typeid)
        slant_df = gsh.run_slant_at_intervals(self.dt1,self.dt2,my_dem_handler) #get the slant df
        receptor_df = ac.slant_df_to_rec_df(slant_df) #convert to a receptor style dataframe
        receptor_path = os.path.join(self.configs.folder_paths['output_folder'],'receptors',self.configs.column_type) #get the path to put the receptor csv in with column type
        fname = self.get_rec_fname() #get the filename
        receptor_fullpath = os.path.join(receptor_path,fname) #join the path
        self.receptor_header(receptor_fullpath,self.dt1,self.dt2) #write the header of the receptor file
        receptor_df.to_csv(receptor_fullpath,mode = 'a',index=False) #append the receptor dataframe to the receptor file after the header

    def receptor_header(self,full_fname,dt1,dt2):
        '''Write a header for to receptor file 
        
        Args:
        full_fname (str) : full path and filename of the file we want to write
        dt1 (datetime.datetime) : start datetime
        dt2 (datetime.datetime) : end datetime
        '''
        with open(full_fname,'w') as f: #open the file
            f.write('Receptor file created using atmos_column.create_receptors\n') #Write some info
            f.write(f'Column type: {self.configs.column_type}\n') #like the column type
            f.write(f'Instrument Location: {self.configs.inst_lat}, {self.configs.inst_lon}, {self.configs.inst_zasl}masl\n')#the instrument info
            f.write(f"Created at: {datetime.datetime.now(tz=datetime.UTC)}\n") #when the code was run
            f.write(f"Data date: {dt1.strftime('%Y-%m-%d')}\n") #the date of the data
            f.write(f"Datetime range: {dt1} to {dt2}\n") #and the range
            f.write('\n')

    def get_rec_fname(self):
        '''Defines the name of a receptor file based on the datetime range 
        
        Returns:
        fname (str) : filename based on the date and datetime range of the class
        '''

        date = self.dt1.strftime('%Y%m%d') #grab the date of the dt1
        t1 = self.dt1.strftime('%H%M%S') #grabe the start time
        t2 = self.dt2.strftime('%H%M%S') #grab the end time
        fname = f'{date}_{t1}_{t2}.csv' #define the filename as YYYYmmdd_HHMMSS_HHMMSS.csv
        return fname

def main():
    '''
    Main run using <python create_receptors.py> will load the configs and create the receptors in 
    output/receptors/{column_type}/YYYYmmdd_HHMMSS_HHMMSS.csv for each day in the config range. 
    '''
    config_json_fname = 'input_config_test.json'
    configs = run_config.run_config_obj(config_json_fname=config_json_fname) #load the configs
    structure_check.directory_checker(configs,run=True) #check the structure
    for dt_range in configs.split_dt_ranges: #iterate by day
        print(f"{dt_range['dt1']} to {dt_range['dt2']}") 
        rec_creator_inst = receptor_creator(configs,dt_range['dt1'],dt_range['dt2']) #create the receptor class
        rec_creator_inst.create_receptors() #create the receptors and save to csv. 

if __name__=='__main__':
    main()


