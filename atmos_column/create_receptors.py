import os
from funcs import ac_funcs as ac
from config import run_config

def em27_rec_creator(configs,oof_filename):
    '''Create and store a receptor file for STILT from a single em27 oof file'''
    print(f'Creating receptors for EM27 column data for {oof_filename}, inclusive {configs.dt1_str} to {configs.dt2_str}.')
    ESH = ac.em27_slant_handler(os.path.join(configs.folder_paths['hrrr_data_folder'],'subsets'),
                            configs.folder_paths['column_data_folder'],
                            configs.folder_paths['output_folder'])

    print(f'Creating slant dataframe for {oof_filename}')
    slant_df = ESH.run_singleday_fromoof(oof_filename,configs.dt1_str,configs.dt2_str,configs.timezone,configs.z_ail_list)
    slant_df_pos = slant_df.loc[slant_df['receptor_zagl']>0]
    if len(slant_df_pos)==0:
        return
    rec_df = ac.slant_df_to_rec_df(slant_df_pos)
    oof_prefix = oof_filename.split('.')[0]
    full_fname = ac.rec_df_full_fname(rec_df,os.path.join(configs.folder_paths['output_folder'],'receptors','for_stilt'),oof_prefix)
    rec_df.to_csv(full_fname,index=False)
    return full_fname

def ground_rec_creator(configs):
    for dt_range in configs.split_dt_ranges:
        dt1 = dt_range['dt1']
        dt2 = dt_range['dt2']
        gsh = ac.ground_slant_handler(configs.inst_lat,
                                      configs.inst_lon,
                                      configs.inst_zasl,
                                      configs.z_ail_list,
                                      configs.folder_paths['hrrr_subset_path'],
                                      configs.hrrr_subset_datestr)
        slant_df = gsh.run_slant_at_intervals(dt1,dt2)
        receptor_df = ac.slant_df_to_rec_df(slant_df)
        gnd_prefix = f"gnd_{dt1.strftime('%Y%m%d')}"
        full_fname = ac.rec_df_full_fname(receptor_df,os.path.join(configs.folder_paths['output_folder'],'receptors','for_stilt'),gnd_prefix)
        receptor_df.to_csv(full_fname,index=False)

def main():
    configs = run_config.run_config_obj()
    if configs.column_type == 'ground':
        ground_rec_creator(configs)
    # if configs.column_type == 'em27':
    #     my_oof_manager = ac.oof_manager(configs.folder_paths['column_data_folder'],configs.timezone)
    #     oof_files_inrange = my_oof_manager.get_oof_in_range(configs.dt1_str,configs.dt2_str)
    #     print(f'Found {len(oof_files_inrange)} oof files in dt range. Analyzing...')
    #     for oof_filename in oof_files_inrange:
    #         em27_rec_creator(configs,oof_filename)

if __name__=='__main__':
    main()


