import os
from funcs import ac_funcs as ac
from config.run_setup_config import *

def em27_rec_creator(folder_paths,dt1_str,dt2_str,timezone,z_ail_list):
    ESH = ac.em27_slant_handler(os.path.join(folder_paths['hrrr_data_folder'],'subsets'),
                            folder_paths['column_data_folder'],
                            folder_paths['output_folder'],
                            hrrr_subset_datestr=hrrr_subset_datestr)
    my_oof_manager = ac.oof_manager(folder_paths['column_data_folder'],timezone)
    oof_files_inrange = my_oof_manager.get_oof_in_range(dt1_str,dt2_str)
    for oof_filename in oof_files_inrange:
        slant_df = ESH.run_singleday_fromoof(oof_filename,dt1_str,dt2_str,timezone,z_ail_list)
        print(slant_df)
def main():
    ac.check_paths(folder_paths)
    if column_type == 'em27':
        em27_rec_creator(folder_paths,dt1_str,dt2_str,timezone,z_ail_list)

if __name__=='__main__':
    main()


