import os
from config import run_config
import subprocess

class em27_stilt_setup:
    def __init__(self,configs,oof_filename,stilt_name='stilt'):
        self.configs = configs
        self.oof_filename = oof_filename
        self.stilt_name = stilt_name

    def full_setup(self):
        stilt_init(self.configs,stilt_name=self.stilt_name)
        receptor_file = self.find_receptor_file()
        print(receptor_file)

    def find_receptor_file(self):
        oof_prefix = self.oof_filename.split('.')[0]
        receptor_path = os.path.join(self.configs.folder_paths['output_folder'],'receptors','for_stilt')
        string_match = 0
        for file in os.listdir(receptor_path):
            if oof_prefix in file:
                good_file = file
                string_match += 1
        if string_match>1:
            raise Exception(f'More than one receptor file with oof identifier {oof_prefix} in {receptor_path}')
        if string_match == 0:
            raise Exception(f'No oof file with the prefix {oof_prefix} found in {receptor_path}')
        return good_file

def stilt_init(configs,stilt_name='stilt'):
    os.chdir(configs.folder_paths['stilt_folder'])
    uataq_command = f"uataq::stilt_init('{stilt_name}')"
    response = subprocess.call(['Rscript','-e', uataq_command]) #this is the official stilt init command

def rewrite_runstilt_r(configs,template_path):
    pass

def main():
    configs = run_config.run_config_obj
    if configs.column_type=='em27':
        ess = em27_stilt_setup(configs,'ha20220616.ada.oof')
        ess.full_setup()
    pass

if __name__=='__main__':
    main()