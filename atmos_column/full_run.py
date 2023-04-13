import os
import create_receptors as cr
import stilt_setup as ss
import funcs.ac_funcs as ac
from config import run_config
from config import structure_check

def main():
    configs = run_config.run_config_obj() #load configuration data
    structure_check.directory_checker(configs,run=True)
    for dt_range in configs.split_dt_ranges:
        print(f"{dt_range['dt1']} to {dt_range['dt2']}")
        rec_creator_inst = cr.receptor_creator(configs,dt_range['dt1'],dt_range['dt2'])
        rec_creator_inst.create_receptors()
        stilt_setup_inst = ss.stilt_setup(configs,dt_range['dt1'],dt_range['dt2'])
        stilt_setup_inst.full_setup()

if __name__=='__main__':
    main()