import os
from config import run_config
import subprocess
import datetime

class stilt_setup:
    def __init__(self,configs,dt1,dt2,stilt_name='stilt'):
        self.configs = configs
        self.dt1 = dt1
        self.dt2 = dt2
        self.stilt_name = stilt_name

    def full_setup(self):
        stilt_init(self.configs,stilt_name=self.stilt_name)
        receptor_files = self.find_receptor_files()
        if len(receptor_files) == 0:
            raise Exception('No receptor files found matching column type in date range')
        self.rewrite_run_stilt(receptor_files)

    def find_receptor_files(self):
        receptor_fullfilenames = []
        receptor_path = os.path.join(self.configs.folder_paths['output_folder'],'receptors')
        daystrings_inrange = self.get_datestrings_inrange()
        for file in os.listdir(receptor_path):
            if self.configs.column_type not in file:
                continue
            for daystring in daystrings_inrange:
                if daystring in file:
                    receptor_fullfilenames.append(os.path.join(receptor_path,file))
        return receptor_fullfilenames

    def get_datestrings_inrange(self):
        daystrings_in_range = [] #initialize the day strings in the range
        delta_days = self.dt2.date()-self.dt1.date() #get the number of days delta between the end and the start
        for i in range(delta_days.days +1): #loop through that number of days 
            day = self.dt1.date() + datetime.timedelta(days=i) #get the day by incrementing by i (how many days past the start)
            daystrings_in_range.append(day.strftime('%Y%m%d')) #append a string of the date (YYYYmmdd) to match with filenames
        return daystrings_in_range
    
    def rewrite_run_stilt(self,receptor_files):
        run_stilt_template_filepath = os.path.join(self.configs.folder_paths['base_project_folder'],'Atmos_Column','atmos_column','config','run_stilt_template.r')
        
        with open(run_stilt_template_filepath,'r') as run_stilt_template_file:
            run_stilt_template_lines = run_stilt_template_file.readlines()
    

def stilt_init(configs,stilt_name='stilt'):
    if os.path.isdir(os.path.join(configs.folder_paths['stilt_folder'],stilt_name,'r')):
        print(f"STILT looks to be set up at {configs.folder_paths['stilt_folder']}/{stilt_name}")
        return
    print(f"STILT not found in {configs.folder_paths['stilt_folder']}/{stilt_name} -- Creating project")
    os.chdir(configs.folder_paths['stilt_folder'])
    uataq_command = f"uataq::stilt_init('{stilt_name}')"
    response = subprocess.call(['Rscript','-e', uataq_command]) #this is the official stilt init command

def main():
    configs = run_config.run_config_obj()
    dt1 = datetime.datetime(2022,6,16,2,0,0,tzinfo=datetime.timezone.utc)
    dt2 = datetime.datetime(2022,6,27,23,0,0,tzinfo=datetime.timezone.utc)
    stilt_setup_inst = stilt_setup(configs,dt1,dt2)
    stilt_setup_inst.full_setup()

if __name__=='__main__':
    main()