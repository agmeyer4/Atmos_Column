import os
from funcs import ac_funcs as ac
from config import run_config, structure_check
import datetime

class receptor_creator:
    def __init__(self,configs):
        self.configs = configs
    
    def create_receptors(self):
        print(f"Creating receptors and saving to {self.configs.folder_paths['output_folder']}")
        if self.configs.column_type == 'ground':
            self.ground_rec_creator()
        elif self.configs.column_type == 'em27':
            self.em27_rec_creator()
        else:
            raise Exception(f'Config column type = {self.configs.column_type} not recognized. Try a recognizable config.')

    def em27_rec_creator(self,configs,oof_filename):
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
        full_fname = ac.rec_df_full_fname(rec_df,os.path.join(configs.folder_paths['output_folder'],'receptors'),oof_prefix)
        rec_df.to_csv(full_fname,index=False)
        return full_fname

    def ground_rec_creator(self):
        print(f'Column type is generic "ground". Creating receptors for {len(self.configs.split_dt_ranges)} dates in range.')
        for dt_range in self.configs.split_dt_ranges:
            print(f"{dt_range['dt1']} to {dt_range['dt2']}")
            dt1 = dt_range['dt1']
            dt2 = dt_range['dt2']
            gsh = ac.ground_slant_handler(self.configs.inst_lat,
                                        self.configs.inst_lon,
                                        self.configs.inst_zasl,
                                        self.configs.z_ail_list,
                                        self.configs.folder_paths['hrrr_subset_path'],
                                        self.configs.hrrr_subset_datestr)
            slant_df = gsh.run_slant_at_intervals(dt1,dt2)
            receptor_df = ac.slant_df_to_rec_df(slant_df)
            prefix = f"{self.configs.column_type}_{dt1.strftime('%Y%m%d')}"
            full_fname = ac.rec_df_full_fname(receptor_df,
                                              os.path.join(self.configs.folder_paths['output_folder'],'receptors'),prefix)
            self.receptor_header(full_fname,dt_range)
            receptor_df.to_csv(full_fname,mode = 'a',index=False)

    def receptor_header(self,full_fname,dt_range):
        with open(full_fname,'w') as f:
            f.write('Receptor file created using atmos_column.create_receptors\n')
            f.write(f'Column type: {self.configs.column_type}')
            f.write(f"Created at: {datetime.datetime.now(tz=datetime.UTC)}\n")
            f.write(f"Data date: {dt_range['dt1'].strftime('%Y-%m-%d')}\n")
            f.write(f"Datetime range: {dt_range['dt1']} to {dt_range['dt2']}\n")
            f.write('\n')

def main():
    configs = run_config.run_config_obj()
    structure_check.directory_checker(configs,run=True)
    rec_creator_inst = receptor_creator(configs)
    rec_creator_inst.create_receptors()

    # if configs.column_type == 'em27':
    #     my_oof_manager = ac.oof_manager(configs.folder_paths['column_data_folder'],configs.timezone)
    #     oof_files_inrange = my_oof_manager.get_oof_in_range(configs.dt1_str,configs.dt2_str)
    #     print(f'Found {len(oof_files_inrange)} oof files in dt range. Analyzing...')
    #     for oof_filename in oof_files_inrange:
    #         em27_rec_creator(configs,oof_filename)

if __name__=='__main__':
    main()


