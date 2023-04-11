import os
from funcs import ac_funcs as ac
from config import run_config, structure_check
import datetime

class receptor_creator:
    def __init__(self,configs,dt1,dt2):
        self.configs = configs
        self.dt1 = dt1
        self.dt2 = dt2
    
    def create_receptors(self):
        print(f"Creating receptors and saving to {self.configs.folder_paths['output_folder']}")
        if self.configs.column_type == 'ground':
            self.ground_rec_creator()
        elif self.configs.column_type == 'em27':
            self.em27_rec_creator()
        else:
            raise Exception(f'Config column type = {self.configs.column_type} not recognized. Try a recognizable config.')

    def em27_rec_creator(self):
        '''Create and store a receptor file for STILT from a single em27 oof file'''
        print(f'Column type is "em27". Slant columns will be created for datetimes with existing oof files')
        print(f'Instrument lat/lon/zasl will be taken from oof files')
        print(f"Creating receptors for {len(self.configs.split_dt_ranges)} dates in range.")

        my_oof_manager = ac.oof_manager(self.configs.folder_paths['column_data_folder'],self.configs.timezone)
        oof_df = my_oof_manager.load_oof_df_inrange(self.dt1,self.dt2)
        if len(oof_df) == 0:
            print(f'No oof data for {self.dt1} to {self.dt2}')
            return
        inst_lat,inst_lon,inst_zasl = my_oof_manager.check_get_loc(oof_df)
    
        gsh = ac.ground_slant_handler(inst_lat,
                                        inst_lon,
                                        inst_zasl,
                                        self.configs.z_ail_list,
                                        self.configs.folder_paths['hrrr_subset_path'],
                                        self.configs.hrrr_subset_datestr)
        
        dt1_oof = oof_df.index[0].floor(self.configs.interval)
        dt2_oof = oof_df.index[-1].ceil(self.configs.interval)
        if dt2_oof > self.dt2:
            dt2_oof = self.dt2
        slant_df = gsh.run_slant_at_intervals(dt1_oof,dt2_oof)
        receptor_df = ac.slant_df_to_rec_df(slant_df)
        receptor_path = os.path.join(self.configs.folder_paths['output_folder'],'receptors',self.configs.column_type)
        fname = self.get_rec_fname()
        receptor_fullpath = os.path.join(receptor_path,fname)
        self.receptor_header(receptor_fullpath,dt1_oof,dt2_oof)
        receptor_df.to_csv(receptor_fullpath,mode = 'a',index=False)

    def ground_rec_creator(self):
        print(f'Column type is generic "ground"')
        print(f'Instrument lat/lon/zasl taken from configs file')
        print(f"Creating receptors for {len(self.configs.split_dt_ranges)} dates in range.")

        gsh = ac.ground_slant_handler(self.configs.inst_lat,
                                    self.configs.inst_lon,
                                    self.configs.inst_zasl,
                                    self.configs.z_ail_list,
                                    self.configs.folder_paths['hrrr_subset_path'],
                                    self.configs.hrrr_subset_datestr)
        slant_df = gsh.run_slant_at_intervals(self.dt1,self.dt2)
        receptor_df = ac.slant_df_to_rec_df(slant_df)
        receptor_path = os.path.join(self.configs.folder_paths['output_folder'],'receptors',self.configs.column_type)
        fname = self.get_rec_fname()
        receptor_fullpath = os.path.join(receptor_path,fname)
        self.receptor_header(receptor_fullpath,self.dt1,self.dt2)
        receptor_df.to_csv(receptor_fullpath,mode = 'a',index=False)

    def receptor_header(self,full_fname,dt1,dt2):
        with open(full_fname,'w') as f:
            f.write('Receptor file created using atmos_column.create_receptors\n')
            f.write(f'Column type: {self.configs.column_type}\n')
            f.write(f"Created at: {datetime.datetime.now(tz=datetime.UTC)}\n")
            f.write(f"Data date: {dt1.strftime('%Y-%m-%d')}\n")
            f.write(f"Datetime range: {dt1} to {dt2}\n")
            f.write('\n')

    def get_rec_fname(self):
        date = self.dt1.strftime('%Y%m%d')
        t1 = self.dt1.strftime('%H%M%S')
        t2 = self.dt2.strftime('%H%M%S')
        fname = f'{date}_{t1}_{t2}.csv'
        return fname


def main():
    configs = run_config.run_config_obj()
    structure_check.directory_checker(configs,run=True)
    for dt_range in configs.split_dt_ranges:
        print(f"{dt_range['dt1']} to {dt_range['dt2']}")
        rec_creator_inst = receptor_creator(configs,dt_range['dt1'],dt_range['dt2'])
        rec_creator_inst.create_receptors()

if __name__=='__main__':
    main()


