import numpy as np
import matplotlib.pyplot as plt
from netCDF4 import Dataset
import os
import pandas as pd
import xarray as xr
from copy import copy
from matplotlib.offsetbox import AnchoredText
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from cartopy.geodesic import Geodesic
import shapely.geometry as sgeom
import datetime
import cartopy.crs as ccrs
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import cartopy.io.img_tiles as cimgt
import pytz
import sys
import os
sys.path.append('..')
import funcs.ac_funcs as ac

def load_oco_df(oco_data_fullpath,quality_flag = 0):
    '''Loads the OCO dataset and filters by quality flag if desired'''
    xr_ds = xr.open_dataset(oco_data_fullpath) #load netcdf to an xarray
    oco_df = xr_ds[['xco2','time','latitude','longitude','xco2_quality_flag']].to_dataframe().reset_index(drop=True) #get a dataframe and only get the columns we want
    oco_df['dt'] = oco_df['time'].dt.tz_localize('UTC') #oco data is in UTC, so add timezone as a dt column
    oco_df = oco_df.drop('time',axis =1) #drop the time column to avoid confusion
    if quality_flag is not None: #if we want to filter on quality flag
        oco_df = oco_df.loc[oco_df['xco2_quality_flag']==quality_flag] #do it
    return oco_df

def trim_oco_df_to_extent(oco_df,extent):
    '''Trims an oco dataframe to an extent dictionary with lat_low, lat_high etc.'''
    trimmed_df = oco_df.copy()
    trimmed_df = trimmed_df.loc[(trimmed_df['longitude']>=extent['lon_low'])&
                                (trimmed_df['longitude']<=extent['lon_high'])&
                                (trimmed_df['latitude']>=extent['lat_low'])&
                                (trimmed_df['latitude']<=extent['lat_high'])]
    return trimmed_df

def add_oco_inradius_column(df,inst_loc,radius_m):
    '''Add a column to the oco df indicating if the lat/lon are in a radius (in meters)'''
    return_df = df.copy()
    return_df['dist_from_inst'] = np.vectorize(ac.haversine)(inst_loc['lat'],inst_loc['lon'],return_df['latitude'],return_df['longitude'])
    return_df['inradius'] = return_df['dist_from_inst']<=radius_m
    return return_df

def get_oco_details(oco_df):
    '''Get the statistical details of an oco df. Would usually pass the dataframe of "inradius" data'''
    if len(oco_df)==0:
        print('No data in oco_df')
        return None
    describe_dict = dict(oco_df['xco2'].describe())
    out_dict = {}
    for k,v in describe_dict.items():
        if k == 'count':
            out_dict['oco_num_soundings'] = v
        else:
            out_dict[f'oco_xco2_{k}'] = v
    out_dict['oco_window_start'] = min(oco_df['dt'])
    out_dict['oco_window_end'] = max(oco_df['dt'])
    return out_dict

def add_oof_inwindow_column(oof_df,oco_details,oof_surround_time):
    '''Add a column to the oof data indicating if it is in the window surrounding an oco dataframe, 
    defined by oof_surround time'''
    oof_df['in_oco_window'] = (oof_df.index>=oco_details['oco_window_start']-oof_surround_time)&(oof_df.index<=oco_details['oco_window_end']+oof_surround_time)
    return oof_df

def get_oof_details(oof_df):
    '''Get the statistical details of an oof df, usually would pass only "inwindow" data'''
    if len(oof_df) == 0:
        print('no data in oof df')
        return None
    describe_dict = oof_df['xco2(ppm)'].describe()
    out_dict = {}
    for k,v in describe_dict.items():
        if k == 'count':
            out_dict['em27_num_obs'] = v
        else:
            out_dict[f'em27_xco2_{k}'] = v
    return out_dict

def bin_oco_soundings(oco_df,step_deg):
    '''Instead of plotting all oco soundings, create an xarray binning them a {step_deg} resolution grid by mean within
    those grid cells'''
    to_bin = lambda x: np.floor(x/step_deg)*step_deg
    oco_df['latbin'] = to_bin(oco_df['latitude'])
    oco_df['lonbin'] = to_bin(oco_df['longitude'])
    binned_xr = oco_df.groupby(['latbin','lonbin']).mean(numeric_only=True).to_xarray()
    return binned_xr

def get_plottext_from_details(oco_details,oof_details):
    '''Creates the textbox for comparing on the plot'''
    text = 'IN RADIUS, IN WINDOW\n\n'
    if oco_details == None:
        oco_text = 'OCO: No soundings in radius'
    else:
        oco_text = f"OCO Soundings = {oco_details['oco_num_soundings']}\n\
OCO XCO2_mean = {oco_details['oco_xco2_mean']:.{2}f}ppm\n\
OCO XCO2_std = {oco_details['oco_xco2_std']:.{2}f}ppm\n\n"

    if oof_details == None:
        oof_text = "EM27: No data in window"
    else: 
        oof_text = f"EM27 Obs = {oof_details['em27_num_obs']}\n\
EM27 XCO2_mean = {oof_details['em27_xco2_mean']:.{2}f}\n\
EM27 XCO2_std = {oof_details['em27_xco2_std']:.{2}f}ppm"

    return text+oco_text+oof_text

def check_for_oco_file(oco_data_folder,date):
    '''Checks for an OCO file for an input date
    
    Args:
    oco_data_folder (str) : path to a directory with OCO .nc files
    date (datetime.date) : date to check for data
    
    Returns:
    oco_filename (str) : name of the oco file for that date. Returns None if there is no file.'''

    oco_date_str = datetime.datetime.strftime(date,'%y%m%d') #format the datetime to how it appears in the oco filenames (yymmdd)
    oco_filename = None #initialize to None
    for fname in os.listdir(oco_data_folder): #go through all the files in the folder
        if oco_date_str in fname: #find the file where the datestring matches one of the files
            oco_filename = fname #set the return to that file
    return oco_filename

def check_for_oof_file(oof_data_folder,date):
    '''Checks an EM27 .oof file for an input date
    
    Args:
    oof_data_folder (str) : path to a directory with EM27 .oof files
    date (datetime.date) : date to check for data
    
    Returns:
    oof_filename (str) : name of the oof file for that date. Returns None if there is no file.'''
    oof_date_str = datetime.datetime.strftime(date,'%Y%m%d') #format the date to how it appears in oof files (yyyymmdd)
    oof_filename = None
    for fname in os.listdir(oof_data_folder):
        if oof_date_str in fname:
            oof_filename = fname
    return oof_filename