'''
Module: oco_funcs.py
Author: Aaron G. Meyer (agmeyer4@gmail.com)
Description: This module contains code for comparing ground based total column (mostly EM27 for now) data with OCO2 and OCO3
soundings. This includes finding, loading, examining, plotting, and comparing these types of data. Running this module via python
will produce an example plot, which can also be found in ../ipynbs/oco_em27_comparison.ipynb
'''

#Import necessary packages
import numpy as np
import matplotlib.pyplot as plt
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
sys.path.append('..')
import funcs.ac_funcs as ac

def load_oco_df(oco_data_fullpath,quality_flag = 0):
    '''Loads the OCO dataset and filters by quality flag if desired
    
    Args: 
    oco_data_fullpath (str): full data path of a single OCO netcdf file -- works with both OCO2 and OCO3 data
    quality_flag (int,float,str): default is 0, which for OCO2 is "good" data. Filters dataframes to keep only rows where
                                    "xco2_quality_flag" in the netcdf equals the input quality_flag
                                    
    Returns:
    oco_df (pd.DataFrame): a dataframe object of all of the oco soundings (quality filtered if applicable) in the netcdf. 
    '''

    xr_ds = xr.open_dataset(oco_data_fullpath) #load netcdf to an xarray
    oco_df = xr_ds[['xco2','time','latitude','longitude','xco2_quality_flag']].to_dataframe().reset_index(drop=True) #get a dataframe and only get the columns we want
    oco_df['dt'] = oco_df['time'].dt.tz_localize('UTC') #oco data is in UTC, so add timezone as a dt column
    oco_df = oco_df.drop('time',axis =1) #drop the time column to avoid confusion
    if quality_flag is not None: #if we want to filter on quality flag
        oco_df = oco_df.loc[oco_df['xco2_quality_flag']==quality_flag] #do it
    return oco_df

def trim_oco_df_to_extent(oco_df,extent):
    '''Trims an oco dataframe to an extent dictionary with lat_low, lat_high etc.
    
    Args:
    oco_df (pd.DataFrame): a pandas dataframe (usually loaded using load_oco_df()) containing at least 'longitude' and 'latitude' columns
    extent (dict): a dictionary defining the extent within which to trim the oco dataframe. Needs to have items 'lat_low','lat_high'
                    'lon_low' and 'lon_high'

    Returns:
    trimmed_df (pd.DataFrame): a pandas dataframe with only points confined to the defined extent box
    '''

    trimmed_df = oco_df.copy() #copy the dataframe to avoid backsetting issues
    trimmed_df = trimmed_df.loc[(trimmed_df['longitude']>=extent['lon_low'])&
                                (trimmed_df['longitude']<=extent['lon_high'])&
                                (trimmed_df['latitude']>=extent['lat_low'])&
                                (trimmed_df['latitude']<=extent['lat_high'])] #trim it
    return trimmed_df

def add_oco_inradius_column(df,inst_loc,radius_m):
    '''Add a column to the oco df indicating if the lat/lon are within a radius (in meters) surrounding a point
    
    Args: 
    df (pd.DataFrame): a pandas dataframe with columns 'latitude' and 'longitude'
    inst_loc (dict): a dictionary of where the point of interest is. Needs keys 'lat' and 'lon'
    radius_m (float): meters from the inst_loc within which to include points as "inradius"

    Returns:
    return_df (pd.DataFrame): the same input dataframe with two new columns 
                              'dist_from_inst'-- how far each row (point) is from the inst_loc using a haversine formula
                              'inradius' -- boolean column indicating if the row is within the radius from the point
    '''

    return_df = df.copy()
    return_df['dist_from_inst'] = np.vectorize(ac.haversine)(inst_loc['lat'],inst_loc['lon'],return_df['latitude'],return_df['longitude'])
    return_df['inradius'] = return_df['dist_from_inst']<=radius_m
    return return_df

def get_oco_details(oco_df):
    '''Get the statistical details of an oco df. Would usually pass the dataframe of "inradius" data
    
    Args:
    oco_df (pd.DataFrame): pandas dataframe of OCO data

    Returns:
    out_dict (dict): dictionary of the statistical features of the input dataframe 
    '''

    if len(oco_df)==0: #if there's no data in the dataframe
        print('No data in oco_df') #let us know
        return None #and return none for the details dict
    describe_dict = dict(oco_df['xco2'].describe()) #use describe to get the statistical features of the dataframe
    out_dict = {} #initialize the official output dictionary
    for k,v in describe_dict.items(): #loop through the items in the stats dict and rename to a helpful name
        if k == 'count': 
            out_dict['oco_num_soundings'] = v
        else:
            out_dict[f'oco_xco2_{k}'] = v
    out_dict['oco_window_start'] = min(oco_df['dt']) #add in the start and end times. this will only be beneficial if the input dataframe is excluded to 'inradius' 
    out_dict['oco_window_end'] = max(oco_df['dt'])
    return out_dict

def add_oof_inwindow_column(oof_df,oco_details,oof_surround_time):
    '''Add a column to the oof data indicating if it is in the window surrounding an oco dataframe, 
    defined by oof_surround time
    
    Args:
    oof_df (pd.DataFrame): pandas dataframe of em27 (oof) data
    oco_details (dict): dictionary created by get_oco_details which includes the start and end windows of the inradius data
    oof_surround_time (datetime.timedelta): how long on either side of the overpass to pad in the oof data

    Returns:
    oof_df (pd.DataFrame): same as the input df, with a boolean column added (in_oco_window) indicating if the measurment falls in the window defined by the start, end and surround times
    '''

    oof_df['in_oco_window'] = (oof_df.index>=oco_details['oco_window_start']-oof_surround_time)&(oof_df.index<=oco_details['oco_window_end']+oof_surround_time)
    return oof_df

def get_oof_details(oof_df):
    '''Get the statistical details of an oof df, usually would pass only "inwindow" data
    
    Args:
    oof_df (pd.DataFrame): pandas dataframe of em27 (oof) data
    
    Returns:
    out_dict (dict) : dictionary of the statistical features of the input dataframe
    '''

    if len(oof_df) == 0: #if there's no data in the oof_df
        print('no data in oof df') #tell us
        return None #and return none for the output dict
    describe_dict = oof_df['xco2(ppm)'].describe() #describe the oof df, specifically for xco2 (what we would want to compare with OCO)
    out_dict = {} #initialize the official output dict
    for k,v in describe_dict.items(): #rename them to a helpful name including em27
        if k == 'count':
            out_dict['em27_num_obs'] = v
        else:
            out_dict[f'em27_xco2_{k}'] = v
    return out_dict

def bin_oco_soundings(oco_df,step_deg):
    '''Instead of including (plotting) all oco soundings, create an xarray binning them a {step_deg} resolution grid by mean within
    those grid cells
    
    Args:
    oco_df (pd.DataFrame): pandas dataframe of oco data
    step_deg (float): size of the grid cells to bin the OCO soundings into. Can be decimal. 

    Returns:
    binned_xr (xarray.DataArray): an xarray object with oco soundings binned into the defined grid resolution
    '''
    to_bin = lambda x: np.floor(x/step_deg)*step_deg #define the lambda for binning
    oco_df['latbin'] = to_bin(oco_df['latitude']) #do it for latitude 
    oco_df['lonbin'] = to_bin(oco_df['longitude']) #do it for longitude
    binned_xr = oco_df.groupby(['latbin','lonbin']).mean(numeric_only=True).to_xarray() #group them and convert to xarray
    return binned_xr

def get_plottext_from_details(oco_details,oof_details):
    '''Creates a textbox for comparing EM27 and OCO data on the plot
    
    Args:
    oco_details (dict): statistical details of oco data, generated using get_oco_details
    oof_details (dict): statistical details of oof (em27) data, generated using get_oof_details
    
    Returns:
    out_text (str): string (with formatting) showing important statistical features of both OCO and OOF input data
    '''
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

    out_text = text+oco_text+oof_text
    return out_text

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

if __name__ == "__main__":
    base_project_dir = '/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1'
    oco_data_folder = os.path.join(base_project_dir,'Data/OCO/OCO2/SLC_targets') #where the oco data is
    oof_data_folder = os.path.join(base_project_dir,'Data/EM27_oof/SLC_EM27_ha_2022_2023_oof_v2_nasrin_correct/') #where the oof data is 
    map_extent={'lon_low':-112.4,
                'lon_high':-111.6,
                'lat_low':40.5,
                'lat_high':41.0} #the extent you want your map to be 
    inst_loc = {'lat':40.768,'lon':-111.854} #location of the instrument
    radius = 6000 #radius around the instrument to consider "good" oco soundings
    oof_surround_time = datetime.timedelta(minutes=30) #padding on either side of the oco overpass to consider comparison em27 data

    oco_filename = 'oco2_LtCO2_221003_B11100Ar_230609093747s.nc4' #name of the oco file
    oof_filename = 'ha20221003.vav.ada.aia.oof' #name of the oof file

    oco_df = load_oco_df(os.path.join(oco_data_folder,oco_filename),quality_flag=0) #load the oco data
    trimmed_oco_df = trim_oco_df_to_extent(oco_df,map_extent) #trim the oco data to the map extent
    trimmed_oco_df = add_oco_inradius_column(trimmed_oco_df,inst_loc,radius) #add the column indicating if the rows are in the "good" radius
    inradius_oco_df = trimmed_oco_df.loc[trimmed_oco_df['inradius']] #to get the mean/std of soundings in the radius, filter to only inradius values
    inradius_oco_details = get_oco_details(inradius_oco_df) #get the oco stat details
 
    my_oof_manager = ac.oof_manager(oof_data_folder,'UTC') #initialize the oof manager
    oof_df = my_oof_manager.df_from_oof(oof_filename,fullformat = True, filter_flag_0=True) #filter and load the oof dataframe
    oof_df = add_oof_inwindow_column(oof_df,inradius_oco_details,oof_surround_time) #add the "inwindow" column for what data corresponds with oco overpass
    inwindow_oof_df = oof_df.loc[oof_df['in_oco_window']] #use only the inwindow data 
    inwindow_oof_details = get_oof_details(inwindow_oof_df) #to get the stats for the EM27 data compared with OCO

    step_deg = 0.02 #grid sizing for OCO plotting instead of points for soundings
    binned_oco_xr = bin_oco_soundings(trimmed_oco_df,step_deg) #create the xarray
    plot_text = get_plottext_from_details(inradius_oco_details,inwindow_oof_details) #create the text for the run

    labsize = 12 #how big the labels are
    proj = ccrs.PlateCarree() #map projection to use
    fig = plt.figure(figsize=(10,8)) #figure size
    ax = plt.axes(projection = proj) #initilize the map axis on the projection
    ax.set_extent([map_extent['lon_low'],map_extent['lon_high'],map_extent['lat_low'],map_extent['lat_high']],crs=proj) #set the map extent
    request = cimgt.GoogleTiles(style='satellite') #source of the background map tiles
    scale = 9.0 #resolution of the map -- this is the bottleneck. Change when you are changing map extents to make it reasonable
    ax.add_image(request,int(scale)) #add the map tile to the plot

    map = binned_oco_xr['xco2'].plot.pcolormesh('lonbin','latbin',ax = ax,alpha=0.7,cmap='viridis',add_colorbar=False) #plot the oco xarray grid
    ax.scatter(inst_loc['lon'],inst_loc['lat'],color = 'red',marker = 'X',s = 100) #plot the instrument location

    cp = Geodesic().circle(lon=inst_loc['lon'],lat=inst_loc['lat'],radius = radius) #create the radius circle
    geom = sgeom.Polygon(cp) #intialize the polygon to plot
    ax.add_geometries(geom,crs=proj,edgecolor = 'k',facecolor='none') #add the circle to the plot

    at = AnchoredText(plot_text, loc='upper left', frameon=True, borderpad=0.5, prop=dict(size=10)) #initialize the textbox
    ax.add_artist(at) #add the textbox to the plot

    axins = inset_axes(ax,width='40%',height='20%',loc='lower left') #creat the inset axis for EM27 data
    axins.scatter(oof_df.index,oof_df['xco2(ppm)'],color = 'grey',zorder=3,s=1) #plot the em28 data on the inset 
    if inwindow_oof_details is not None: #if there is data in the good window, create a highlight box around it
            window_base = (min(oof_df.loc[oof_df['in_oco_window']].index),min(oof_df['xco2(ppm)'])) #bottom left corner of the highlight box
            width = max(oof_df.loc[oof_df['in_oco_window']].index)-min(oof_df.loc[oof_df['in_oco_window']].index) #width of the highlight box
            height = max(oof_df['xco2(ppm)'])-min(oof_df['xco2(ppm)'])+0.2 #height of the highlight box
            rect = mpatches.Rectangle((window_base),width,height,zorder = 10,alpha = 0.5) #create the rectangle patch
            axins.add_patch(rect) #add the rectangle to the plot
    axins.tick_params(labelsize = labsize) #Set the size of the inset axis lables
    axins.set_ylabel('EM27 XCO2 (ppm)',size = labsize-3) #set the inset y label
    #axins.set_ylim([415,425])
    axins.xaxis.set_major_formatter(mdates.DateFormatter('%H', tz = datetime.timezone.utc)) #set the format for the inset x axis
    axins.set_xlabel(oof_df.index[0].strftime('%Z %b %d, %Y'),size = labsize) #set x axis title based on datetime
    plt.gcf().autofmt_xdate() #format the xaxis 
    plt.colorbar(map,fraction=0.03,label ='XCO2 (ppm)') #add the colorbar
    plt.show() #show the plot