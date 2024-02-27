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
from funcs import ac_funcs as ac
from config import run_config, structure_check

class receptor_creator:
    '''
    A class used to create receptors based on input configurations
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
    
    def create_receptors(self,my_dem_handler):
        '''
        Creates the receptors and saves them to the correct output/receptors folder based on column type and other configs
        TODO: Add more types of receptor creators (methaneAIR, satellites, etc)        
        '''

        print(f"Creating receptors and saving to {self.configs.folder_paths['output_folder']}")
        if self.configs.column_type == 'ground':
            return self.ground_rec_creator(my_dem_handler)
        elif self.configs.column_type == 'em27':
            return self.em27_rec_creator(my_dem_handler)
        else:
            raise Exception(f'Config column type = {self.configs.column_type} not recognized. Try a recognizable config.')

    def em27_rec_creator(self,my_dem_handler):
        '''Create and store a receptor file for STILT using EM27 data to define certain parameters
        
        Most importantly, this method will overwrite the lat/lon/zasl in the configs file using the data directly from
        the em27 oof files. This method will also clip days to the length of the oof data, rather than running all hours
        when the sun is up. 
        '''

        print(f'Column type is "em27". Slant columns will be created for datetimes with existing oof files')
        print(f'Instrument lat/lon/zasl will be taken from oof files')

        my_oof_manager = ac.oof_manager(self.configs.folder_paths['column_data_folder'],self.configs.timezone) #create the oof manager
        oof_df = my_oof_manager.load_oof_df_inrange(self.dt1,self.dt2) #load the oof data in the required range
        if len(oof_df) == 0: #if there isn't any oof data in that range
            print(f'No oof data for {self.dt1} to {self.dt2}') #tell us
            return -1#and return a flag
        inst_lat,inst_lon,inst_zasl = my_oof_manager.check_get_loc(oof_df) #grab the instrument lat/lon/zasl from the oof dataframe and check to make sure it's the same
        gsh = ac.ground_slant_handler(inst_lat,inst_lon,inst_zasl,self.configs.z_ail_list) #create the slant handler   
        self.configs.inst_lat,self.configs.inst_lon,self.configs.inst_zasl = inst_lat,inst_lon,inst_zasl #add the inst location taken from oof to the config object
        
        #Run from the interval before the start and after the end of the oof dataframe, rather than the whole day (clip to oof data)   
        dt1_oof = oof_df.index[0].floor(self.configs.interval)  #floor is rounding down to the nearest interval
        dt2_oof = oof_df.index[-1].ceil(self.configs.interval) #ceil is rounding up to the nearest interval
        if dt2_oof > self.dt2: #we don't want to go past dt2
            dt2_oof = self.dt2 #so set it equal if the last dt in the oof file is bigger -- this happens when it runs past midnight often

        stilt_rec = ac.StiltReceptors(self.configs,self.dt1,self.dt2) #initilize the stilt receptor instance
        stilt_rec.create_for_stilt() #create the file and write the header
        slant_df = gsh.run_slant_at_intervals(dt1_oof,dt2_oof,my_dem_handler,interval=self.configs.interval) #Get the slant column between the oof datetimes
        receptor_df = ac.slant_df_to_rec_df(slant_df) #transform it to a receptor dataframe style
        stilt_rec.append_df(receptor_df) #add the dataframe to the receptor file
        return 0 #return success


    def ground_rec_creator(self,my_dem_handler):
        '''Create and store a receptor file for STILT using a generic "ground" slant column with interval
        
        This method will use all of the parameters in the input_configs, and has nothing to do with oof files or em27 data. 
        '''

        print(f'Column type is generic "ground"')
        print(f'Instrument lat/lon/zasl taken from configs file')
        print(f"Creating receptors for {len(self.configs.split_dt_ranges)} dates in range.")
        gsh = ac.ground_slant_handler(self.configs.inst_lat,
                                    self.configs.inst_lon,
                                    self.configs.inst_zasl,
                                    self.configs.z_ail_list) #create the slant handler

        stilt_rec = ac.StiltReceptors(self.configs,self.dt1,self.dt2) #initilize the stilt receptor instance
        stilt_rec.create_for_stilt() #create the file and write the header
        slant_df = gsh.run_slant_at_intervals(self.dt1,self.dt2,my_dem_handler) #get the slant df
        receptor_df = ac.slant_df_to_rec_df(slant_df) #convert to a receptor style dataframe
        stilt_rec.append_df(receptor_df)
        return 0 #return success

def main():
    '''
    Main run using <python create_receptors.py> will load the configs and create the receptors in 
    output/receptors/{column_type}/YYYYmmdd_HHMMSS_HHMMSS.csv for each day in the config range. 
    '''
    config_json_fname = 'input_config_fulltest.json'
    configs = run_config.run_config_obj(config_json_fname=config_json_fname) #load the configs
    structure_check.directory_checker(configs,run=True) #check the structure
    my_dem_handler = ac.DEM_handler(configs.folder_paths['dem_folder'],configs.dem_fname,configs.dem_typeid)
    for dt_range in configs.split_dt_ranges: #iterate by day
        print(f"{dt_range['dt1']} to {dt_range['dt2']}") 
        rec_creator_inst = receptor_creator(configs,dt_range['dt1'],dt_range['dt2']) #create the receptor class
        rec_creator_inst.create_receptors(my_dem_handler) #create the receptors and save to csv. 


if __name__=='__main__':
    main()


