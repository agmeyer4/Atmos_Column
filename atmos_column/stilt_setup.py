import os
from config import run_config, structure_check
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
        self.rewrite_run_stilt(receptor_fnames)
        self.move_new_runstilt()

    def find_receptor_files(self):
        receptor_fnames = []
        receptor_path = os.path.join(self.configs.folder_paths['output_folder'],'receptors',self.configs.column_type)
        daystrings_inrange = self.get_datestrings_inrange()
        for file in os.listdir(receptor_path):
            for daystring in daystrings_inrange:
                if daystring in file:
                    receptor_fnames.append(os.path.join(file))
        return receptor_fnames

    def get_datestrings_inrange(self):
        daystrings_in_range = [] #initialize the day strings in the range
        delta_days = self.dt2.date()-self.dt1.date() #get the number of days delta between the end and the start
        for i in range(delta_days.days +1): #loop through that number of days 
            day = self.dt1.date() + datetime.timedelta(days=i) #get the day by incrementing by i (how many days past the start)
            daystrings_in_range.append(day.strftime('%Y%m%d')) #append a string of the date (YYYYmmdd) to match with filenames
        return daystrings_in_range
    
    def rewrite_run_stilt(self,receptor_fnames):
        print('Rewriting the ac_run_stilt.r file to current configuration')
        original_run_stilt_filepath = os.path.join(self.configs.folder_paths['stilt_folder'],self.stilt_name,'r','run_stilt.r')
        new_run_stilt_filepath = os.path.join(self.configs.folder_paths['base_project_folder'],'Atmos_Column','atmos_column','temp','ac_run_stilt.r')
        receptor_loader_filepath = os.path.join(self.configs.folder_paths['base_project_folder'],'Atmos_Column','atmos_column','funcs','receptor_loader.r')

        run_stilt_configs = self.configs.run_stilt_configs
        run_stilt_configs['n_cores'] = self.configs.cores

        with open(original_run_stilt_filepath,'r') as original_run_stilt_file:
            original_run_stilt_lines = original_run_stilt_file.readlines()
        with open(receptor_loader_filepath,'r') as receptor_loader_file:
            receptor_loader_lines = receptor_loader_file.readlines()
        
        new_run_stilt_file = open(new_run_stilt_filepath,'w')

        for i in range(0,11): #The first 11 lines are correct and contain paths setup during the stilt initialization
            new_run_stilt_file.write(original_run_stilt_lines[i])

        #Next we want the receptors. We need the paths and filenames first
        path_line_str,filenames_line_str = self.receptor_path_line_creator(receptor_fnames)
        new_run_stilt_file.write(path_line_str+'\n')
        new_run_stilt_file.write(filenames_line_str+'\n\n')
        #Next we need the code to load multiple receptor files with headers
        for receptor_loader_line in receptor_loader_lines:
            new_run_stilt_file.write(receptor_loader_line)
        new_run_stilt_file.write('\n\n')

        for i in range(11,len(original_run_stilt_lines)):
            if (i>21)&(i<38):
                continue
            line = original_run_stilt_lines[i]
            line_split = line.split()
            if len(line_split)==0:
                new_run_stilt_file.write(line)
                continue
            if line_split[0] in run_stilt_configs.keys():
                if line_split[1] == '<-':
                    new_run_stilt_file.write(' '.join([line_split[0],line_split[1],str(run_stilt_configs[line_split[0]])]))
                    new_run_stilt_file.write('\n')
                else:
                    new_run_stilt_file.write(line)
            else:
                new_run_stilt_file.write(line)
        
        new_run_stilt_file.close()

    def receptor_path_line_creator(self,receptor_fnames):
        path_line_str = "rec_path <- '{}/{}/{}'".format(self.configs.folder_paths['output_folder'],'receptors',self.configs.column_type)
        filenames_line_str = "rec_filenames <- c("
        for receptor_fname in receptor_fnames:
            filenames_line_str = filenames_line_str+f"'{receptor_fname}',"
        filenames_line_str = filenames_line_str[:-1]+')'
        return path_line_str,filenames_line_str
        
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

class met_handler:
    def __init__(self,configs,dt1,dt2,n_hours):
        self.configs = configs
        self.dt1 = dt1
        self.dt2 = dt2
        self.n_hours = n_hours

    def get_met(self):
        #This doesn't work yet because I can just use the HRRR files on our CHPC system. Need to figure out how to download for sharable use
        dts = self.get_dt_str_list()
        for dt in dts:
            pass
        met_path = "'{}'".format(os.path.join(self.configs.folder_paths['hrrr_data_folder'],self.configs.met_model_type))
        met_file_format = f"'%Y%m%d/hrrr.t%H*'"
        return {'met_path':met_path,'met_file_format':met_file_format}
        
    def get_dt_str_list(self):
        dt_str_format = '%Y-%m-%d %H:%M'
        dts = []
        dt = self.dt1 + datetime.timedelta(hours=self.n_hours)
        while dt <= self.dt2:
            dts.append(dt.strftime(dt_str_format))
            dt = dt + datetime.timedelta(hours=1)
        return dts

def main():
    configs = run_config.run_config_obj()
    structure_check.directory_checker(configs,run=True)

    stilt_setup_inst = stilt_setup(configs,configs.start_dt,configs.end_dt)
    stilt_setup_inst.full_setup()

if __name__=='__main__':
    main()