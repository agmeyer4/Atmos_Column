import os
from config import run_config
import subprocess
import datetime
from herbie import Herbie

class stilt_setup:
    def __init__(self,configs,dt1,dt2,stilt_name='stilt'):
        self.configs = configs
        self.dt1 = dt1
        self.dt2 = dt2
        self.stilt_name = stilt_name

    def full_setup(self):
        stilt_init(self.configs,stilt_name=self.stilt_name)
        receptor_fnames = self.find_receptor_files()
        if len(receptor_fnames) == 0:
            raise Exception('No receptor files found matching column type in date range')
        self.rewrite_run_stilt(receptor_fnames,'config_run_stilt.r')
        self.move_new_runstilt()

    def find_receptor_files(self):
        receptor_fullfilenames = []
        receptor_path = os.path.join(self.configs.folder_paths['output_folder'],'receptors',self.configs.column_type)
        daystrings_inrange = self.get_datestrings_inrange()
        for file in os.listdir(receptor_path):
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
    
    def rewrite_run_stilt(self,receptor_fnames,run_template_fname):
        print('Rewriting the ac_run_stilt.r file to current configuration')
        template_run_stilt_filepath = os.path.join(self.configs.folder_paths['base_project_folder'],'Atmos_Column','atmos_column','config',run_template_fname)
        original_run_stilt_filepath = os.path.join(self.configs.folder_paths['stilt_folder'],self.stilt_name,'r','run_stilt.r')
        new_run_stilt_filepath = os.path.join(self.configs.folder_paths['base_project_folder'],'Atmos_Column','atmos_column','temp','ac_run_stilt.r')

        with open(original_run_stilt_filepath,'r') as original_run_stilt_file:
            original_run_stilt_lines = original_run_stilt_file.readlines()
        with open(template_run_stilt_filepath,'r') as template_run_stilt_file:
            template_run_stilt_lines = template_run_stilt_file.readlines()
        with open(new_run_stilt_filepath,'w') as new_run_stilt_file:
            for i in range(0,11):
                new_run_stilt_file.write(original_run_stilt_lines[i])
            path_line_str,filenames_line_str = self.receptor_path_line_creator(receptor_fnames)
            new_run_stilt_file.write(path_line_str+'\n')
            new_run_stilt_file.write(filenames_line_str+'\n\n')
            new_run_stilt_file.write(self.hrrr_path_line_creator()+'\n')
            for line in template_run_stilt_lines:
                new_run_stilt_file.write(line)
    
    def receptor_path_line_creator(self,receptor_fnames):
        path_line_str = "rec_path <- '{}/{}/{}'".format(self.configs.folder_paths['output_folder'],'receptors',self.configs.column_type)
        filenames_line_str = "rec_filenames <- c("
        for receptor_fname in receptor_fnames:
            filenames_line_str = filenames_line_str+f"'{receptor_fname}',"
        filenames_line_str = filenames_line_str[:-1]+')'
        return path_line_str,filenames_line_str
    
    def hrrr_path_line_creator(self):
        hrrr_path = "met_path <- '{}'".format(self.configs.folder_paths['hrrr_data_folder'])
        return hrrr_path
    
    def move_new_runstilt(self):
        print('Moving new ac_run_stilt.r to the STILT directory')
        new_run_stilt_path = os.path.join(self.configs.folder_paths['base_project_folder'],'Atmos_Column','atmos_column','temp')
        new_run_stilt_fname = 'ac_run_stilt.r'
        official_run_stilt_path = os.path.join(self.configs.folder_paths['stilt_folder'],self.stilt_name,'r')
        os.rename(os.path.join(new_run_stilt_path,new_run_stilt_fname),os.path.join(official_run_stilt_path,new_run_stilt_fname))

def stilt_init(configs,stilt_name='stilt'):
    if os.path.isdir(os.path.join(configs.folder_paths['stilt_folder'],stilt_name,'r')):
        print(f"STILT looks to be set up at {configs.folder_paths['stilt_folder']}/{stilt_name}")
        return
    print(f"STILT not found in {configs.folder_paths['stilt_folder']}/{stilt_name} -- Creating project")
    os.chdir(configs.folder_paths['stilt_folder'])
    uataq_command = f"uataq::stilt_init('{stilt_name}')"
    response = subprocess.call(['Rscript','-e', uataq_command]) #this is the official stilt init command

class hrrr_handler:
    def __init__(self,configs,dt1,dt2,n_hours):
        self.configs = configs
        self.dt1 = dt1
        self.dt2 = dt2
        self.n_hours = n_hours

    def get_hrrr(self):
        dts = self.get_dt_str_list()
        for dt in dts:
            H = Herbie(dt,model='hrrr',product='prs',fxx=0,save_dir=f"{self.configs.folder_paths['hrrr_data_folder']}") #setup the herbie subset
            print(H.PRODUCTS)
            #H.download()   #download the height dataset
        pass
    def get_dt_str_list(self):
        dt_str_format = '%Y-%m-%d %H:%M'
        dts = []
        dt = self.dt1 - datetime.timedelta(hours=self.n_hours)
        while dt <= self.dt2:
            dts.append(dt.strftime(dt_str_format))
            dt = dt + datetime.timedelta(hours=1)
        return dts

def main():
    configs = run_config.run_config_obj()
    dt1 = datetime.datetime(2022,6,16,2,0,0,tzinfo=datetime.timezone.utc)
    dt2 = datetime.datetime(2022,6,16,2,0,0,tzinfo=datetime.timezone.utc)
    # stilt_setup_inst = stilt_setup(configs,dt1,dt2)
    # stilt_setup_inst.full_setup()
    hrrr_inst = hrrr_handler(configs,dt1,dt2,1)
    hrrr_inst.get_hrrr()
if __name__=='__main__':
    main()