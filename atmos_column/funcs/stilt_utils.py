'''
Module: stilt_utils.py
Author: Aaron G. Meyer (agmeyer4@gmail.com)
Description: 
This module is used to load and configure the configs jsons in the same folder. See input_config_description.txt for more information
about what the input_config.json type files contain and how to edit. 
'''

#Imports
import numpy as np
import datetime
import pytz
import os
import yaml

class StiltConfig:
    '''
    The main configuration object. Stores all necessary parameters from the YAML config file,
    handles timezone localization, and prepares UTC datetimes for backend processing.
    '''

    def __init__(self, config_path=None, config_yaml_fname='input_config.yaml'):
        '''
        Args:
        config_yaml_fname (str): Name of the YAML config file. Defaults to 'input_config.yaml'.
        '''
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')

        self.config_yaml_fullpath = os.path.join(config_path, config_yaml_fname)
        yaml_data = self.load_yaml()

        for key in yaml_data:
            setattr(self, key, yaml_data[key])

        # Timezone-aware datetime parsing
        self.start_dt_local = self.dtstr_to_dttz(self.start_dt_str, self.timezone)
        self.end_dt_local = self.dtstr_to_dttz(self.end_dt_str, self.timezone)

        # Convert to UTC for internal usage
        self.start_dt_utc = self.start_dt_local.astimezone(pytz.UTC)
        self.end_dt_utc = self.end_dt_local.astimezone(pytz.UTC)

        # Split datetime ranges in UTC
        self.split_dt_ranges = self.get_split_dt_ranges()

        # Adjust MET settings
        self.adjust_met()

        # Set tmp folder
        self.folder_paths['tmp_folder'] = os.path.join(
            self.folder_paths['Atmos_Column_folder'], 'tmp')

    def adjust_met(self):
        '''Adjusts MET folder paths and download logic.'''
        if self.download_met == 'T':
            if self.folder_paths['met_folder'] == "stilt_parent":
                stilt_parent = os.path.split(self.folder_paths['stilt_folder'])[0]
                met_folder = os.path.join(stilt_parent, 'met')
                if not os.path.exists(met_folder):
                    os.makedirs(met_folder)
                self.folder_paths['met_folder'] = met_folder
                self.run_stilt_configs['met_path'] = f"'{met_folder}'"
            elif not os.path.exists(self.folder_paths['met_folder']):
                raise ValueError('Error: MET folder does not exist and is not set to stilt_parent.')
        else:
            self.folder_paths['met_folder'] = self.run_stilt_configs['met_path'][1:-1]  # strip quotes

    def load_yaml(self):
        '''Loads the YAML configuration file.'''
        with open(self.config_yaml_fullpath) as f:
            yaml_data = yaml.safe_load(f)
        return yaml_data

    def dtstr_to_dttz(self, dt_str, timezone):
        '''
        Converts a string to a timezone-aware datetime object.

        Args:
        dt_str (str or datetime.datetime): Input datetime string.
        timezone (str): Timezone string (e.g., 'UTC', 'US/Mountain')

        Returns:
        datetime.datetime: Timezone-aware datetime
        '''
        if isinstance(dt_str, str):
            dt = datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        elif isinstance(dt_str, datetime.datetime):
            dt = dt_str
        else:
            raise ValueError('Error: dt_str must be a string or datetime object.')
        return pytz.timezone(timezone).localize(dt)

    def get_split_dt_ranges(self):
        '''
        Splits the UTC datetime range into daily chunks.

        Returns:
        list: List of dictionaries with 'dt1' and 'dt2' keys in UTC.
        '''
        if self.start_dt_utc > self.end_dt_utc:
            raise ValueError('Error: Start datetime is after end datetime.')

        split_dt_list = []
        current = self.start_dt_utc
        while current.date() <= self.end_dt_utc.date():
            if current.date() == self.start_dt_utc.date():
                dt1 = self.start_dt_utc
                dt2 = datetime.datetime.combine(current.date(), datetime.time(23, 59, 59), tzinfo=pytz.UTC)
            elif current.date() == self.end_dt_utc.date():
                dt1 = datetime.datetime.combine(current.date(), datetime.time(0, 0, 0), tzinfo=pytz.UTC)
                dt2 = self.end_dt_utc
            else:
                dt1 = datetime.datetime.combine(current.date(), datetime.time(0, 0, 0), tzinfo=pytz.UTC)
                dt2 = datetime.datetime.combine(current.date(), datetime.time(23, 59, 59), tzinfo=pytz.UTC)
            split_dt_list.append({'dt1': dt1, 'dt2': dt2})
            current += datetime.timedelta(days=1)

        return split_dt_list


def main():
    configs = StiltConfig(config_yaml_fname='input_config.yaml')
    print("Start (local):", configs.start_dt_local)
    print("End (local):", configs.end_dt_local)
    print("Start (UTC):", configs.start_dt_utc)
    print("End (UTC):", configs.end_dt_utc)
    print("Daily UTC splits:")
    for rng in configs.split_dt_ranges:
        print(f"  {rng['dt1']} to {rng['dt2']}")


if __name__ == '__main__':
    main()
