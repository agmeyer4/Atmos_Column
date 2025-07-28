'''
Module: stilt_setup.py
Author: Aaron G. Meyer (agmeyer4@gmail.com)
Description: 
This module is used for setting up STILT runs based on configurations in the associated config file. The stilt_setup class
contains methods required to make the STILT project, find the correct receptor files based on a datetime range, and setup 
the run_stilt.r file for running STILT with the configs in the config file. 
'''

import os
import subprocess
import datetime
import shutil
import sys

class stilt_setup:
    '''This class sets up a STILT run based on the configs and datetime inputs'''

    def __init__(self, configs, dt1, dt2, stilt_name=None):
        '''
        Args:
        configs (obj of type run_config_obj): configurations from a config yaml file to use 
        dt1 (datetime.datetime): start datetime
        dt2 (datetime.datetime): end datetime
        stilt_name (str): name of the STILT project to go inside the configs.folder_paths['stilt_folder']. Default='YYYYMMDD' of dt1
        '''
        self.configs = configs
        self.dt1 = dt1
        self.dt2 = dt2
        if stilt_name is None:
            self.stilt_name = dt1.strftime('%Y%m%d')
        else:
            self.stilt_name = stilt_name

    def full_setup(self):
        '''Performs the full setup for a STILT project.'''
        successful_setup = False
        while not successful_setup:
            response = self.stilt_init()
            if int(response) == 0:
                successful_setup = True
                break
            else:
                what_to_do = self.get_what_to_do(response)
                if what_to_do == 'c':
                    break
                elif what_to_do == 'd':
                    print('deleting and retrying')
                    stilt_fullpath_to_del = os.path.join(self.configs.folder_paths['stilt_folder'], self.stilt_name)
                    subprocess.call(['rm', '-rf', stilt_fullpath_to_del])
                    continue
                elif what_to_do == 'e':
                    sys.exit('Stopping operation here')

        self.create_rec_folder_in_stilt()
        receptor_fnames = self.find_receptor_files()
        self.mv_recfile_to_stiltdir(receptor_fnames)
        self.create_config_folder_in_stilt()
        self.cp_configfile_to_stiltdir()
        if len(receptor_fnames) == 0:
            raise Exception('No receptor files found matching column type in date range')
        self.rewrite_run_stilt(receptor_fnames)
        self.move_new_runstilt()
        if self.configs.download_met == 'T':
            from funcs import ac_funcs as ac
            hrrr_getter = ac.HRRR_ARL_Getter(self.configs, self.dt1, self.dt2)
            hrrr_getter.get_hrrr_met()

    def get_what_to_do(self, response):
        if response == -1:
            print('Do you want to continue with current setup (c), delete and resetup (d), or exit altogether (e)?\n') 
        else:
            print('Stilt setup failed likely due to random bug (see terminal output). \nDo you want to delete the folder and resetup (d) or exit altogether (e)? ')
        what_to_do = ''
        while what_to_do not in ['c', 'd', 'e']:
            what_to_do = input(f'Enter (c/d/e): ')
        return what_to_do

    def create_rec_folder_in_stilt(self):
        rec_folder = os.path.join(self.configs.folder_paths['stilt_folder'], self.stilt_name, 'receptors')
        if os.path.isdir(rec_folder):
            print('receptor folder already exists in the stilt directory')
            return
        os.mkdir(rec_folder)

    def create_config_folder_in_stilt(self):
        config_folder = os.path.join(self.configs.folder_paths['stilt_folder'], self.stilt_name, 'config')
        if os.path.isdir(config_folder):
            print('config folder already exists in the stilt directory')
            return
        os.mkdir(config_folder)

    def find_receptor_files(self):
        '''Finds the receptor files in output/receptors/{column_type} that match the datetime range criteria'''
        receptor_fnames = []
        receptor_path = os.path.join(self.configs.folder_paths['output_folder'], 'receptors', self.configs.column_type)
        daystrings_inrange = self.get_datestrings_inrange()
        for file in os.listdir(receptor_path):
            for daystring in daystrings_inrange:
                if daystring in file:
                    receptor_fnames.append(os.path.join(file))
        return receptor_fnames

    def get_datestrings_inrange(self):
        '''Gets strings of dates within the datetime range that will match the label of the receptor filenames'''
        daystrings_in_range = []
        delta_days = self.dt2.date() - self.dt1.date()
        for i in range(delta_days.days + 1):
            day = self.dt1.date() + datetime.timedelta(days=i)
            daystrings_in_range.append(day.strftime('%Y%m%d'))
        return daystrings_in_range

    def mv_recfile_to_stiltdir(self, receptor_fnames):
        '''Moves the receptor file to the appropriate directory within the STILT project folder'''
        for receptor_fname in receptor_fnames:
            os.popen(f"mv {os.path.join(self.configs.folder_paths['output_folder'], 'receptors', self.configs.column_type, receptor_fname)} {os.path.join(self.configs.folder_paths['stilt_folder'], self.stilt_name, 'receptors', receptor_fname)}")

    def cp_configfile_to_stiltdir(self):
        '''Copies the configuration file from the local config path to the STILT project folder for reference'''
        os.popen(f"cp {self.configs.config_yaml_fullpath} {os.path.join(self.configs.folder_paths['stilt_folder'], self.stilt_name, 'config', os.path.split(self.configs.config_yaml_fullpath)[1])}")

    def rewrite_run_stilt(self, receptor_fnames):
        """
        Rewrites the run_stilt.r file for the current configuration.
        Inserts library lines from config after the 4th line of the template.
        """
        print('Rewriting the ac_run_stilt.r file to current configuration')

        # Define file paths
        original_run_stilt_filepath = os.path.join(
            self.configs.folder_paths['stilt_folder'], self.stilt_name, 'r', 'run_stilt.r'
        )
        new_run_stilt_filepath = os.path.join(
            self.configs.folder_paths['base_project_folder'],
            'Atmos_Column', 'atmos_column', 'temp', 'ac_run_stilt.r'
        )
        receptor_loader_filepath = os.path.join(
            self.configs.folder_paths['base_project_folder'],
            'Atmos_Column', 'atmos_column', 'funcs', 'receptor_loader.r'
        )

        run_stilt_configs = self.configs.run_stilt_configs
        run_stilt_configs['n_cores'] = self.configs.slurm_options['ntasks']

        with open(original_run_stilt_filepath, 'r') as orig, \
             open(receptor_loader_filepath, 'r') as loader, \
             open(new_run_stilt_filepath, 'w') as newfile:

            original_lines = orig.readlines()
            loader_lines = loader.readlines()

            # Write lines 0-3 (first 4 lines) from the template
            for i in range(0, 4):
                newfile.write(original_lines[i])

            # Write library lines from config (after line 4, before line 5)
            self.write_run_stilt_lib_lines(newfile)

            # Write line 4 (the 5th line, 0-indexed)
            newfile.write(original_lines[4])

            # Write lines 5-10 (user input section, etc.)
            for i in range(5, 11):
                newfile.write(original_lines[i])

            # Write receptor section
            self.write_receptor_section(newfile, receptor_fnames)

            # Write receptor loader code
            self.write_receptor_loader_code(newfile, loader_lines)

            # Write the main body of the R script, replacing config values as needed
            self.write_main_body(newfile, original_lines, run_stilt_configs)

    def write_run_stilt_lib_lines(self, file):
        """
        Write any R library() lines from the config to the run_stilt.r file after the 4th line.

        Args:
            file (file object): The open file object to write to.
        """
        lib_lines = getattr(self.configs, 'run_stilt_lib_lines', None)
        if lib_lines:
            for line in lib_lines:
                file.write(line + '\n')
            file.write('\n')  # Add a blank line after libraries for readability

    def write_receptor_section(self, file, receptor_fnames):
        """
        Write the receptor path and filenames section to the R script.

        Args:
            file (file object): The open file object to write to.
            receptor_fnames (list): List of receptor filenames.
        """
        path_line_str, filenames_line_str = self.receptor_path_line_creator(receptor_fnames)
        file.write(path_line_str + '\n')
        file.write(filenames_line_str + '\n\n')

    def write_receptor_loader_code(self, file, loader_lines):
        """
        Write the custom receptor loader R code to the script.

        Args:
            file (file object): The open file object to write to.
            loader_lines (list): List of lines from the receptor loader R script.
        """
        for line in loader_lines:
            file.write(line)
        file.write('\n\n')  # Add spacing for readability

    def write_main_body(self, file, original_lines, run_stilt_configs):
        """
        Write the main body of the R script, replacing config values as needed,
        including skipping original multi-line assignments.
        """
        i = 11  # start of main body

        while i < len(original_lines):
            # Skip hardcoded block (receptor + slurm)
            if 16 <= i <= 37:
                i += 1
                continue

            line = original_lines[i]
            stripped = line.strip()
            tokens = stripped.split()

            if not stripped:
                file.write(line)
                i += 1
                continue

            # Check for variable assignment
            if len(tokens) >= 3 and tokens[1] == '<-' and tokens[0] in run_stilt_configs:
                key = tokens[0]
                val = run_stilt_configs[key]
                file.write(f"{key} <- {val}\n")

                # Skip original assignment block (single- or multi-line)
                # Start counting open and close parens
                paren_diff = line.count('(') - line.count(')')
                i += 1
                while paren_diff > 0 and i < len(original_lines):
                    next_line = original_lines[i]
                    paren_diff += next_line.count('(') - next_line.count(')')
                    i += 1
                continue

            # Special case for simulation_id
            if len(tokens) >= 3 and tokens[0] == 'simulation_id' and tokens[1] == '<-':
                file.write("simulation_id <- receptors$sim_id\n")
                # Skip original simulation_id assignment (in case it's multiline)
                paren_diff = line.count('(') - line.count(')')
                i += 1
                while paren_diff > 0 and i < len(original_lines):
                    next_line = original_lines[i]
                    paren_diff += next_line.count('(') - next_line.count(')')
                    i += 1
                continue

            # Default: copy line as-is
            file.write(line)
            i += 1

    def receptor_path_line_creator(self, receptor_fnames):
        """
        Creates the necessary lines to add to the run_stilt.r file based on the receptor fnames and configs.

        Args:
            receptor_fnames (list): List of receptor filenames to go into the run_stilt.r file.

        Returns:
            tuple: (path_line_str, filenames_line_str)
        """
        path_line_str = "rec_path <- '{}/{}/{}'".format(
            self.configs.folder_paths['stilt_folder'], self.stilt_name, 'receptors'
        )
        filenames_line_str = "rec_filenames <- c(" + ",".join(f"'{fname}'" for fname in receptor_fnames) + ")"
        return path_line_str, filenames_line_str

    def move_new_runstilt(self):
        '''Moves the newly written ac_run_stilt.r file to the stilt project directory'''
        print('Moving new ac_run_stilt.r to the STILT directory')
        new_run_stilt_path = os.path.join(
            self.configs.folder_paths['base_project_folder'], 'Atmos_Column', 'atmos_column', 'temp'
        )
        new_run_stilt_fname = 'ac_run_stilt.r'
        official_run_stilt_path = os.path.join(
            self.configs.folder_paths['stilt_folder'], self.stilt_name, 'r'
        )
        shutil.move(
            os.path.join(new_run_stilt_path, new_run_stilt_fname),
            os.path.join(official_run_stilt_path, new_run_stilt_fname)
        )

    def stilt_init(self):
        '''Method to initialize the STILT project if it isn't already'''
        if os.path.isdir(os.path.join(self.configs.folder_paths['stilt_folder'], self.stilt_name, 'r')):
            print(f"STILT looks to be set up at {self.configs.folder_paths['stilt_folder']}/{self.stilt_name}") 
            return -1
        print(f"STILT not found in {self.configs.folder_paths['stilt_folder']}/{self.stilt_name} -- Creating project")
        os.chdir(self.configs.folder_paths['stilt_folder'])
        uataq_command = f"uataq::stilt_init('{self.stilt_name}')"
        response = subprocess.call(['Rscript', '-e', uataq_command])
        return response

def main():
    '''This main function will setup the stilt project using the configuration file'''
    from config import run_config, structure_check
    config_yaml_fname = 'input_config.yaml'
    configs = run_config.run_config_obj(config_yaml_fname=config_yaml_fname)
    structure_check.directory_checker(configs, run=True)

    for dt_range in configs.split_dt_ranges:  # iterate by day
        print(f"{dt_range['dt1']} to {dt_range['dt2']}")
        stilt_setup_inst = stilt_setup(configs, dt_range['dt1'], dt_range['dt2'])
        stilt_setup_inst.full_setup()

if __name__ == '__main__':
    main()