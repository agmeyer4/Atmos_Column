import os
#import run_config
#TODO stilt directory check

class directory_checker:
    def __init__(self,configs,run=False):
        self.configs = configs
        if run:
            self.full_check()
    
    def full_check(self):
        print('Checking Paths')
        self.check_base_existence()
        self.check_output()
        self.check_hrrr_subset()

    def check_base_existence(self):
        for key,path in self.configs.folder_paths.items():
            if not os.path.isdir(path):
                    raise FileNotFoundError(f'Path not found for {key} at {path} Check to ensure your paths are correctly configured in configs/run_config.py.')

    def check_output(self):
        output_path = self.configs.folder_paths['output_folder']
        if not os.path.isdir(os.path.join(output_path,'receptors')):
            os.mkdir(os.path.join(output_path,'receptors'))

    def check_hrrr_subset(self):
        if not os.path.isdir(os.path.join(self.configs.folder_paths['hrrr_data_folder'],'subsets')):
            os.mkdir(os.path.join(self.configs.folder_paths['hrrr_data_folder'],'subsets'))

def main():
    # configs = run_config.run_config_obj #load the configs 
    # dir_check = directory_checker(configs)
    # dir_check.full_check()
    pass

if __name__=='__main__':
    main()