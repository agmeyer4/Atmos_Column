'''
Module: full_run.py
Author: Aaron G. Meyer (agmeyer4@gmail.com)
Description: This module allows the user to do a "full run" of atmospheric column analysis. Running <python full_run.py> will do the following.

1. Read the specified configuration file in atmos_column/config. This provides the parameters for the run. 
2. Check the project structure to ensure that the directories are set up as they should be. 
3. Setup the slurm submit script for running stilt, write its header
4. Iterate through each day in the datetime range of the config file. For each day, steps 4-X will be carried out. 
5. Create the receptors for the run. These are often slant columns for ground based instruments, filtered based on if 
   there is em27 data, or simply an hourly interval for ground data. Created receptors are stored in atmos_column/output/receptors.
   Aircraft data is TODO. 
6. The STILT model is structured and checked. This includes initializing the STILT project in the correct place if needed,
   rewriting the run_stilt.r script to match the created receptor files, and using any extra configs in the configuration file are 
   included in run_stilt. 
7. Add the Rscript line for running stilt to the slurm submit script
8. Ask if user wants to actually submit the slurm script.
9. Submit if so, exit if not
TODO dont define DEM every loop -- make as input to create receptors and only define once. 
TODO apply the averaging kernel and pressure weighting functions
TODO final analysis and storage 
'''

#Import necessary packages
import create_receptors as cr
import stilt_setup as ss
from config import run_config, structure_check
import funcs.ac_funcs as ac

def main():
    config_json_fname = 'input_config_fulltest.json'
    configs = run_config.run_config_obj(config_json_fname=config_json_fname) #load configuration data from atmos_column/config
    structure_check.directory_checker(configs,run=True) #check the structure

    slurm = ac.SlurmHandler(configs) #create a slurm handler from the configs
    slurm.stilt_setup() #create a slurm submit.sh file 

    for dt_range in configs.split_dt_ranges: #go day by day using the split datetime ranges created during run_config.run_config_obj()
        print(f"{dt_range['dt1']} to {dt_range['dt2']}") 
        rec_creator_inst = cr.receptor_creator(configs,dt_range['dt1'],dt_range['dt2']) #Create the receptor creator class
        rec_creator_inst.create_receptors() #create the receptors
        stilt_setup_inst = ss.stilt_setup(configs,dt_range['dt1'],dt_range['dt2']) #create the stilt setup class
        stilt_setup_inst.full_setup() #do a full stilt setup

        slurm.add_stilt_run(stilt_setup_inst.stilt_name) #add this day's run to the slurm file
    
    #Ask if user wants to actually run the slurm file -- not automatic behavior. 
    userin = '' #initialize a userinput
    while (userin != 'y') & (userin != 'n'): #want it to be "y" or "n"
        print('Do you want to submit the slurm job?')
        userin = input('enter y or n: ') #ask if they want to submit

    if userin == 'y': #if they do
        print(f"Submitting {slurm.full_filepath} with sbatch") # print the call
        slurm.submit_sbatch()
    else:
        print('Setup complete, *****Slurm not submitted*****')

if __name__=='__main__':
    main()