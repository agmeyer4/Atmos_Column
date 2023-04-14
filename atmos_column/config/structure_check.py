'''
Module: structure_check.py
Author: Aaron G. Meyer (agmeyer4@gmail.com)
Description: 
This module is used to check to make sure that the folders are setup correctly for doing column and stilt analysis
'''

import os
#TODO stilt directory check

class directory_checker:
    '''This class checks to make sure paths are set up correctly based on input configs'''

    def __init__(self,configs,run=False,column_options=['ground','em27']):
        '''
        Args:
        configs (obj of type run_config_obj) : configuration settings 
        run (bool) : if true, run the full check. Default False
        column_options (list) : list of column types that are possible
        '''

        self.configs = configs
        self.column_options = column_options
        if run:
            self.full_check()
    
    def full_check(self):
        '''Runs the full check'''

        print('Checking Paths')
        self.check_base_existence() #make sure base paths exist
        self.check_output() #make sure the output strucutre is correct
        self.check_hrrr_subset() #make sure the hrrr subset folder is correct

    def check_base_existence(self):
        '''Checks to make sure each path in the configs file is actually there'''

        for key,path in self.configs.folder_paths.items():
            if not os.path.isdir(path):
                    raise FileNotFoundError(f'Path not found for {key} at {path} Check to ensure your paths are correctly configured in configs/run_config.py.')

    def check_output(self):
        '''Checks and configures the output folder'''
        output_path = self.configs.folder_paths['output_folder'] #here's the output path from the configs file
        if not os.path.isdir(os.path.join(output_path,'receptors')): #within output there should be a receptos folder
            os.mkdir(os.path.join(output_path,'receptors')) #so if there isn't, make one
        for column_type in self.column_options: #there should also be a subfolder within receptors for each of the possible column types
            if not os.path.isdir(os.path.join(output_path,'receptors',column_type)): #so if there isn't,
                os.mkdir(os.path.join(output_path,'receptors',column_type)) #make one

    def check_hrrr_subset(self):
        '''Check and configure the hrrr subset folder for getting the surface heights. '''
        if not os.path.isdir(os.path.join(self.configs.folder_paths['hrrr_data_folder'],'subsets')):
            os.mkdir(os.path.join(self.configs.folder_paths['hrrr_data_folder'],'subsets'))

def main():
    # configs = run_config.run_config_obj #load the configs 
    # dir_check = directory_checker(configs)
    # dir_check.full_check()
    pass

if __name__=='__main__':
    main()