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
6. Run stilt
7. TODO apply the averaging kernel and pressure weighting functions
8. TODO final analysis and storage 
'''

#Import necessary packages
import os
import create_receptors as cr
import stilt_setup as ss
from config import run_config, structure_check
import subprocess
import sys

class SlurmHandler:
    def __init__(self,configs,custom_submit_name = None):
        '''
        Args:
        configs (obj of type run_config_obj) : configurations from a config json file to use 
        custom_submit_name (str) : if you would like a custom job submission name, define it here. Will default None to 'submit.sh'
        '''
        self.configs = configs
        if custom_submit_name is None:
            custom_submit_name = 'submit.sh'
        self.full_filepath = os.path.join(self.configs.folder_paths['slurm_folder'],'jobs',custom_submit_name)
    
    def create_submitfile_from_configs(self):
        header = self.create_slurm_header()
        self.write_as_new_file(header)

    def create_slurm_header(self):
        header_lines = []
        header_lines.append('#!/bin/bash')
        for key,value in self.configs.slurm_options.items():
            header_lines.append(f"#SBATCH --{key}={value}")
        log_path = os.path.join(self.configs.folder_paths['slurm_folder'],'logs',"%A.out")
        header_lines.append(f"#SBATCH -o {log_path}")
        header_lines.append('\n')
        header = '\n'.join(header_lines)
        return header
    
    def append_to_file(self,text):
        with open(self.full_filepath,'a') as f:
            f.write(text+'\n')

    def write_as_new_file(self,text):
        with open(self.full_filepath,'w') as f:
            f.write(text+'\n')
def main():
    config_json_fname = 'input_config_test1.json'
    configs = run_config.run_config_obj(config_json_fname=config_json_fname) #load configuration data from atmos_column/config
    structure_check.directory_checker(configs,run=True) #check the structure

    slurm = SlurmHandler(configs)
    slurm.create_submitfile_from_configs()

    for dt_range in configs.split_dt_ranges: #go day by day using the split datetime ranges created during run_config.run_config_obj()
        print(f"{dt_range['dt1']} to {dt_range['dt2']}") 
        stilt_name = f"{dt_range['dt1'].year:04}{dt_range['dt1'].month:02}{dt_range['dt1'].day:02}_stilt"
        rec_creator_inst = cr.receptor_creator(configs,dt_range['dt1'],dt_range['dt2']) #Create the receptor creator class
        rec_creator_inst.create_receptors() #create the receptors
        stilt_setup_inst = ss.stilt_setup(configs,dt_range['dt1'],dt_range['dt2'],stilt_name = stilt_name) #create the stilt setup class
        stilt_setup_inst.full_setup() #do a full stilt setup

        #print(f'Running ac_run_stilt.r for {dt_range}')
        slurm_line = f"Rscript {os.path.join(configs.folder_paths['stilt_folder'],stilt_name,'r','ac_run_stilt.r')}"
        slurm.append_to_file(slurm_line)
        #subprocess.call(['Rscript', os.path.join(configs.folder_paths['stilt_folder'],stilt_name,'r','ac_run_stilt.r')]) #run stilt

if __name__=='__main__':
    main()