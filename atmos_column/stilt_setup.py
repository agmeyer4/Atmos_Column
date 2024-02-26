'''
Module: stilt_setup.py
Author: Aaron G. Meyer (agmeyer4@gmail.com)
Description: 
This module is used for setting up STILT runs based on configurations in the associated config file. The stilt_setup class
contains methods required to make the STILT project, find the correct receptor files based on a datetime range, and setup 
the run_stilt.r file for running STILT with the configs in the config file. 
'''

#Imports
import os
from config import run_config, structure_check
import subprocess
import datetime
import shutil
import sys

class stilt_setup:
    '''This class sets up a STILT run based on the configs and datetime inputs'''

    def __init__(self,configs,dt1,dt2,stilt_name=None):
        '''
        Args:
        configs (obj of type run_config_obj) : configurations from a config json file to use 
        dt1 (datetime.datetime) : start datetime
        dt2 (datetime.datetime) : end datetime
        stilt_name (str) : name of the STILT project to go inside the configs.folder_paths['stilt_folder']. Default='YYYYMMDD' of dt1
        '''

        self.configs = configs
        self.dt1 = dt1
        self.dt2 = dt2
        if stilt_name is None: #default case -- make it dt1
            self.stilt_name = dt1.strftime('%Y%m%d')

    def full_setup(self):
        '''This does the full setup for a STILT project by creating it if necessary, finding receptors, and rewriting/moving run_stilt.r
        TODO make it so that you can subselect what type of receptor files you want to use for the run. Right now it just grabs all (and will run multiple)
        for all receptor files that fit the date criteria in find_resceptor_files. '''
        
        #There is a weird bug where sometimes the stilt initialization script doesn't work -- this is a hack to catch that and try again
        successful_setup=False
        while successful_setup == False:
            response = self.stilt_init() #initialize the stilt project if necessary, grab the response
            if int(response)==0: #0 is a successful setup, so exit this
                successful_setup = True
            else: #if it wasn't successful, keep trying. this could maybe cause an infinite loop if some other aspect of the setup is going awry consistently
                print('stilt setup failed likely due to random bug (see terminal output).')
                stilt_fullpath_to_del =os.path.join(self.configs.folder_paths['stilt_folder'],self.stilt_name)
                retry = input(f'Do you want to delete the folder {stilt_fullpath_to_del} and try again (y/n): ')
                if retry == 'y':
                    print('deleting and retrying')
                    del_statement = f"rm -rf {stilt_fullpath_to_del}"
                    os.popen(del_statement)
                    continue
                else:
                    sys.exit('Stopping operation here')

        self.create_rec_folder_in_stilt()
        receptor_fnames = self.find_receptor_files() #find the receptor files that fit the config and datetime range criteria
        self.mv_recfile_to_stiltdir(receptor_fnames)
        self.create_config_folder_in_stilt() #make a folder in the stilt project to copy config to
        self.cp_configfile_to_stiltdir() #copy the config in
        if len(receptor_fnames) == 0: #if there aren't any files in the range
            raise Exception('No receptor files found matching column type in date range') #raise an exception
        self.rewrite_run_stilt(receptor_fnames) #rewrite the run_stilt.r file with the correct configs and receptors
        self.move_new_runstilt() #move the newly rewritten run_stilt file to the STILT project directory 

    def create_rec_folder_in_stilt(self):
        rec_folder = os.path.join(self.configs.folder_paths['stilt_folder'],self.stilt_name,'receptors')
        if os.path.isdir(rec_folder):
            print('receptor folder already exists in the stilt directory')
            return
        os.mkdir(rec_folder)

    def create_config_folder_in_stilt(self):
        config_folder = os.path.join(self.configs.folder_paths['stilt_folder'],self.stilt_name,'config')
        if os.path.isdir(config_folder):
            print('config folder already exists in the stilt directory')
            return
        os.mkdir(config_folder)

    def find_receptor_files(self):
        '''Finds the receptor files in atmos_column/output/receptors/{column_type} that match the datetime range criteria
        '''

        receptor_fnames = [] #initialize the list
        receptor_path = os.path.join(self.configs.folder_paths['output_folder'],'receptors',self.configs.column_type) #path to receptor files based on configs
        daystrings_inrange = self.get_datestrings_inrange() #gets the dates within the datetime range which will appear in the receptor filenames
        for file in os.listdir(receptor_path): #loop through the receptor files
            for daystring in daystrings_inrange: #for each of the date strings
                if daystring in file: #check if the date is in the filename
                    receptor_fnames.append(os.path.join(file)) #if it is, add it to the good list, otherwise just keep going
        return receptor_fnames #return the names of receptor files in the correct folder within the datetime range

    def get_datestrings_inrange(self):
        '''Gets strings of dates within the datetime range that will match the label of the receptor filenames'''

        daystrings_in_range = [] #initialize the day strings in the range
        delta_days = self.dt2.date()-self.dt1.date() #get the number of days delta between the end and the start
        for i in range(delta_days.days +1): #loop through that number of days 
            day = self.dt1.date() + datetime.timedelta(days=i) #get the day by incrementing by i (how many days past the start)
            daystrings_in_range.append(day.strftime('%Y%m%d')) #append a string of the date (YYYYmmdd) to match with filenames
        return daystrings_in_range

    def mv_recfile_to_stiltdir(self,receptor_fnames):
        '''Moves the receptor file to the appropriate directory within the STILT project folder'''

        for receptor_fname in receptor_fnames:
            os.popen(f"mv {os.path.join(self.configs.folder_paths['output_folder'],'receptors',self.configs.column_type,receptor_fname)} {os.path.join(self.configs.folder_paths['stilt_folder'],self.stilt_name,'receptors',receptor_fname)}")

    def cp_configfile_to_stiltdir(self):
        '''Copies the configuration file from the local config path to the STILT project folder for reference'''
        
        os.popen(f"cp {self.configs.config_json_fullpath} {os.path.join(self.configs.folder_paths['stilt_folder'],self.stilt_name,'config',os.path.split(self.configs.config_json_fullpath)[1])}")

    def rewrite_run_stilt(self,receptor_fnames):
        '''This method rewrites the original run_stilt.r file in the STILT/r directory to match the configurations needed. The newly written 
        file is saved to atmos_column/temp/ac_run_stilt.r. 
        
        There may be a better way to do this, but it works for now. 

        Args:
        receptor_fnames (list) : list of filenames for the receptor files to be included in the STILT run. 
        '''

        print('Rewriting the ac_run_stilt.r file to current configuration')

        #Define some filepaths that we will need to read from to write the new file
        original_run_stilt_filepath = os.path.join(self.configs.folder_paths['stilt_folder'],self.stilt_name,'r','run_stilt.r') #the original run_stilt.r file in the stilt directory
        new_run_stilt_filepath = os.path.join(self.configs.folder_paths['base_project_folder'],'Atmos_Column','atmos_column','temp','ac_run_stilt.r') #where to save the newly written file
        receptor_loader_filepath = os.path.join(self.configs.folder_paths['base_project_folder'],'Atmos_Column','atmos_column','funcs','receptor_loader.r') #an r method to read multiple receptor files
        
        #load the run_stilt_configs from the config file. Within configs.run_stilt_configs, the user can put in any of the same parameters
        #that show up in run_stilt.r, and these parameters will be written into the new run_stilt.r file. 
        run_stilt_configs = self.configs.run_stilt_configs #load the configs
        run_stilt_configs['n_cores'] = self.configs.slurm_options['ntasks'] #make sure n_cores is in the run stilt configs based on teh cores parameter in configs

        #Open and read the lines of the original run_stilt.r and the receptor loader. Pieces of these will be written to the new file
        with open(original_run_stilt_filepath,'r') as original_run_stilt_file:
            original_run_stilt_lines = original_run_stilt_file.readlines()
        with open(receptor_loader_filepath,'r') as receptor_loader_file:
            receptor_loader_lines = receptor_loader_file.readlines()
        
        #Open the new file for writing
        new_run_stilt_file = open(new_run_stilt_filepath,'w')

        for i in range(0,11): #The first 11 lines are correct and contain paths setup during the stilt initialization
            new_run_stilt_file.write(original_run_stilt_lines[i]) #so write those to the new file
            
        #Next we want the receptors. We need the paths and filenames first
        path_line_str,filenames_line_str = self.receptor_path_line_creator(receptor_fnames) #get the path and filenames
        new_run_stilt_file.write(path_line_str+'\n') #write these to the new file
        new_run_stilt_file.write(filenames_line_str+'\n\n')

        #Next we need the code to load multiple receptor files with headers from the receptor_loader file. 
        for receptor_loader_line in receptor_loader_lines:
            new_run_stilt_file.write(receptor_loader_line) #write these code lines to the new file
        new_run_stilt_file.write('\n\n') #add some newlines for readability

        #now we go through the rest of the original run_stilt file and write the necessary parts to the new file
        for i in range(11,len(original_run_stilt_lines)): #loop through the lines of the file
            if (i>21)&(i<38): #the lines between 21 and 38 are the original receptor definitions. 
                              #Since we already wrote the receptor files and loader above to the new file, 
                              #just skip these lines (don't write them to the new file.)
                continue
            line = original_run_stilt_lines[i] #grab the original line
            line_split = line.split() #split the original line on whitespace
            if len(line_split)==0: #if it's a blank line, it will break the line_split[0] in teh next block,
                new_run_stilt_file.write(line) #so just write the blank line
                continue #and move on to the next line
            if line_split[0] in run_stilt_configs.keys(): #check if the first element of the line is a parameter in run_stilt_configs
                #also check if the second element is "<-". These are the parameters we can reset. 
                #If the second element is "=", it's in the stilt_apply function and we don't want to rewrite that. 
                if line_split[1] == '<-': 
                    #write the new parameter from run_stilt_configs, instead of the original parameter
                    new_run_stilt_file.write(' '.join([line_split[0],line_split[1],str(run_stilt_configs[line_split[0]])])) 
                    new_run_stilt_file.write('\n')
                else: #if the second element isnt '<-', we don't want to replace it 
                    new_run_stilt_file.write(line) #so just write the line
            elif line_split[0] == 'simulation_id': #replace the simulation ID line with the sim_id column from receptors
                    if line_split[1] == '<-':
                        new_run_stilt_file.write(' '.join([line_split[0],line_split[1],'receptors$sim_id'])) 
                        new_run_stilt_file.write('\n')      
                    else:
                        new_run_stilt_file.write(line)          
            else: #if the line doesn't have a new value in run_stilt_configs
                new_run_stilt_file.write(line) #just write the original line
        new_run_stilt_file.close() #close the file

    def receptor_path_line_creator(self,receptor_fnames):
        '''Creates the necessary lines to add to the run_stilt.r file based on the receptor fnames and configs
        
        Args:
        receptor_fnames (list) : list of receptor filenames to go into the run_stilt.r file. 
        '''

        #write the path line string based on the configurations and filepaths
        path_line_str = "rec_path <- '{}/{}/{}'".format(self.configs.folder_paths['stilt_folder'],self.stilt_name,'receptors')
        
        #write the filenames string. we want it to be an array of strings when written in the run_stilt.r file, so append each one
        filenames_line_str = "rec_filenames <- c(" #start with the variable name and start the character array 
        for receptor_fname in receptor_fnames: #loop through the receptor filenames
            filenames_line_str = filenames_line_str+f"'{receptor_fname}'," #append each one to the string, with a comma afterward
        filenames_line_str = filenames_line_str[:-1]+')' #delete the final comma, and add the closing parethases
        return path_line_str,filenames_line_str
        
    def move_new_runstilt(self):
        '''Moves the newly written ac_run_stilt.r file to the stilt project directory'''

        print('Moving new ac_run_stilt.r to the STILT directory')
        new_run_stilt_path = os.path.join(self.configs.folder_paths['base_project_folder'],'Atmos_Column','atmos_column','temp') #where it should be stored
        new_run_stilt_fname = 'ac_run_stilt.r' #should be this name
        official_run_stilt_path = os.path.join(self.configs.folder_paths['stilt_folder'],self.stilt_name,'r') #path to the stilt project r directory
        #os.rename(os.path.join(new_run_stilt_path,new_run_stilt_fname),os.path.join(official_run_stilt_path,new_run_stilt_fname)) #move the file
        shutil.move(os.path.join(new_run_stilt_path,new_run_stilt_fname),os.path.join(official_run_stilt_path,new_run_stilt_fname))

    def stilt_init(self):
        '''Method to initialize the STILT project if it isn't already
        
        Args: 
        configs (obj of type run_stilt_obj) : contains the path information we will need
        stilt_name (str) : name of the stilt project within the stilt folder defined in configs
        '''

        if os.path.isdir(os.path.join(self.configs.folder_paths['stilt_folder'],self.stilt_name,'r')): #a good bet if there is a folder named "r" in the stilt directory
            print(f"STILT looks to be set up at {self.configs.folder_paths['stilt_folder']}/{self.stilt_name}") 
            return
        
        #If there isn't, we want to create it 
        print(f"STILT not found in {self.configs.folder_paths['stilt_folder']}/{self.stilt_name} -- Creating project")
        os.chdir(self.configs.folder_paths['stilt_folder']) #change into the stilt folder
        uataq_command = f"uataq::stilt_init('{self.stilt_name}')" #write the uataq command to be joined with the subprocess call
        response = subprocess.call(['Rscript','-e', uataq_command]) #this is the official stilt init command
        return response

class met_handler:
    '''A class to handle getting the met data for running STILT 
    
    This is on hold and TODO
    
    '''

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
    '''This main function will setup the stilt project using the configuration file'''
    config_json_fname = 'input_config_sstest.json'
    configs = run_config.run_config_obj(config_json_fname=config_json_fname)
    structure_check.directory_checker(configs,run=True)

    stilt_setup_inst = stilt_setup(configs,configs.start_dt,configs.end_dt)#,stilt_name = 'sstest')
    stilt_setup_inst.full_setup()

if __name__=='__main__':
    main()