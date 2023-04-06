import os
import create_receptors as cr
import funcs.ac_funcs as ac
from config import run_config
from config import structure_check

def em27_full_run(configs):
    my_oof_manager = ac.oof_manager(configs.folder_paths['column_data_folder'],configs.timezone)
    oof_files_inrange = my_oof_manager.get_oof_in_range(configs.dt1_str,configs.dt2_str)
    print(f'Found {len(oof_files_inrange)} oof files in dt range. Analyzing...')
    for oof_filename in oof_files_inrange:
        cr.em27_rec_creator(configs,oof_filename)#create the receptor and log file
        #configure stilt for the run
        #run stilt
        #analyze stilt output
        #format and finalize output
        #delete unecessary data files
    pass

def main():
    configs = run_config.run_config_obj #load configuration data
    dir_check = structure_check.directory_checker(configs) #load the directory checker class
    dir_check.full_check() #full check the directory setup 

    if configs.column_type == 'em27':
        em27_full_run(configs)
    pass

if __name__=='__main__':
    main()