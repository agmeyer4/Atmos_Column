'''
Module: full_run.py
Author: Aaron G. Meyer (agmeyer4@gmail.com)
Description: This module allows the user to do a "full run" of atmospheric column analysis. Running <python full_run.py> will do the following.

1. Read the specified configuration file in atmos_column/config. This provides the parameters for the run. 
2. Check the project structure to ensure that the directories are set up as they should be. 
3. Iterate through each day in the datetime range of the config file. For each day, steps 4-X will be carried out. 
4. Create the receptors for the run. These are often slant columns for ground based instruments, filtered based on if 
   there is em27 data, or simply an hourly interval for ground data. Created receptors are stored in atmos_column/output/receptors.
   Aircraft data is TODO. 
5. The STILT model is structured and checked. This includes initializing the STILT project in the correct place if needed,
   rewriting the run_stilt.r script to match the created receptor files, and using any extra configs in the configuration file are 
   included in run_stilt. 
6. TODO run stilt
7. TODO apply the averaging kernel and pressure weighting functions
8. TODO final analysis and storage 
'''

#Import necessary packages
import os
import create_receptors as cr
import stilt_setup as ss
from config import run_config, structure_check

def main():
    configs = run_config.run_config_obj(config_json_fname='input_config.json') #load configuration data from atmos_column/config
    structure_check.directory_checker(configs,run=True) #check the structure
    for dt_range in configs.split_dt_ranges: #go day by day using the split datetime ranges created during run_config.run_config_obj()
        print(f"{dt_range['dt1']} to {dt_range['dt2']}") 
        rec_creator_inst = cr.receptor_creator(configs,dt_range['dt1'],dt_range['dt2']) #Create the receptor creator class
        rec_creator_inst.create_receptors() #create the receptors
        stilt_setup_inst = ss.stilt_setup(configs,dt_range['dt1'],dt_range['dt2'],stilt_name = 'stilt2') #create the stilt setup class
        stilt_setup_inst.full_setup() #do a full stilt setup

if __name__=='__main__':
    main()