'''
Module: ac_funcs.py
Author: Aaron G. Meyer (agmeyer4@gmail.com)
Description: This module contains functions and classes for doing atmospheric column analysis as part of the 
atmos_column package. Included are functions for loading and transforming oof data files from the EM27, dealing with slant columns,
loading HRRR data for terrain information, and producing receptor files for running STILT
'''

###################################################################################################################################
# Import Necessary Packages
###################################################################################################################################
import pandas as pd
import numpy as np
import os
import datetime
import itertools
from ftplib import FTP
import shutil
import subprocess
import pytz
import git
import string
import re
import pysolar.solar as solar
from geographiclib.geodesic import Geodesic
from herbie import Herbie
import xarray as xr

###################################################################################################################################
# Define Functions     
###################################################################################################################################
def get_git_hash(path = '.'):
    '''Gets the current git hash
    
    Args:
    path (str) : full path to the git repo, default current dir

    Returns:
    sha (str) : the git hash of the input directory
    '''

    repo = git.Repo(path = path,search_parent_directories = True)
    sha = repo.head.object.hexsha
    return sha

def wdws_to_uv(ws,wd):
    '''Converts a wind speed and direction to u/v vector
    Ref: http://colaweb.gmu.edu/dev/clim301/lectures/wind/wind-uv#:~:text=A%20positive%20u%20wind%20is,wind%20is%20from%20the%20north.

    Args:
    ws (float) : wind speed (magnitude of wind vector)
    wd (float) : wind direction (in degrees, clockwise from north)

    Returns:
    u (float) : u component of wind vector (positive u wind is from west)
    v (float) : v component of wind vector (positiv v wind is from south)
    '''
    wd_math_ref = 270-wd #get to mathematical direction from meteorological direction
    if ws < 0.01: #with very low winds, just set to 0 so we dont get weird values
        u=v=0
        return u,v
    u = ws*np.cos(np.deg2rad(wd_math_ref)) #u is the cosine 
    v = ws*np.sin(np.deg2rad(wd_math_ref)) #v is the sine
    return u,v

def uv_to_wdws(u,v):
    '''Converts a u,v wind vector to meteorological wind speed and direction
    Ref: http://colaweb.gmu.edu/dev/clim301/lectures/wind/wind-uv#:~:text=A%20positive%20u%20wind%20is,wind%20is%20from%20the%20north.

    Args:
    u (float) : u component of wind vector (positive u wind is from west)
    v (float) : v component of wind vector (positiv v wind is from south)

    Returns:
    ws (float) : wind speed (magnitude of wind vector)
    wd (float) : wind direction (in degrees, clockwise from north)
    '''    
    ws = np.sqrt(u**2+v**2) #wind speed is just the magnitude
    if ws <0.01: #deal with very low winds -- wind direction undefined at low winds
        wd = np.nan
        return ws,wd
    wd_math_ref = np.rad2deg(np.arctan2(v,u)) #get the wind direciton
    wd_met_ref = 270-wd_math_ref #shift to meteorological reference

    if wd_met_ref<0: #the above returns values between -180 and 180, so add 360 to negative values to get output between 0 and 360
        wd_met_ref = wd_met_ref+360
    elif wd_met_ref > 360:
        wd_met_ref = wd_met_ref-360
    return ws,wd_met_ref

def uv_to_wswd(u,v):
    '''Converts a u,v wind vector to meteorological wind speed and direction
    Ref: http://colaweb.gmu.edu/dev/clim301/lectures/wind/wind-uv#:~:text=A%20positive%20u%20wind%20is,wind%20is%20from%20the%20north.

    Args:
    u (float) : u component of wind vector (positive u wind is from west)
    v (float) : v component of wind vector (positiv v wind is from south)

    Returns:
    ws (float) : wind speed (magnitude of wind vector)
    wd (float) : wind direction (in degrees, clockwise from north)
    '''    
    ws = np.sqrt(u**2+v**2) #wind speed is just the magnitude
    if ws <0.01: #deal with very low winds -- wind direction undefined at low winds
        wd = np.nan
        return ws,wd
    wd_math_ref = np.rad2deg(np.arctan2(v,u)) #get the wind direciton
    wd_met_ref = 270-wd_math_ref #shift to meteorological reference

    if wd_met_ref<0: #the above returns values between -180 and 180, so add 360 to negative values to get output between 0 and 360
        wd_met_ref = wd_met_ref+360
    elif wd_met_ref > 360:
        wd_met_ref = wd_met_ref-360
    return ws,wd_met_ref

def slant_df_to_rec_df(df,lati_colname='receptor_lat',long_colname='receptor_lon',zagl_colname='receptor_zagl',run_times_colname='dt',rec_is_agl_colname='receptor_z_is_agl'):
    '''Converts a slant dataframe to the form required for a receptor dataframe, including the column names that can be read by r stilt
    
    Args:
    df (pd.DataFrame) : slant style dataframe 
    lati_colname (str) : column name in the slant df corresponding to the receptor latitude, to be named 'lati' in the receptor df
    long_colname (str) : column name in the slant df corresponding to the receptor longitude, to be named 'long' in the receptor df
    zagl_colname (str) : column name in the slant df corresponding to the receptor zagl, to be named 'zagl' in the receptor df
    run_times_colname (str) : column name in the slant df corresponding to the receptor datetune, to be named 'run_times' in the receptor df
    rec_is_agl_colname (str) : column name in the slant df corresponding to whether the receptor is above ground level, to be named 'z_is_agl' in the receptor df
    
    Returns:
    df1 (pd.DataFrame) : dataframe that can be written to a csv and function as a receptor file for stilt, with the correct column names
    '''
    
    print('Changing slant df to receptor style df')
    df1 = df.copy() #copy the df
    df1 = df1.reset_index() #reset the index to get the dt in a column
    df1 = df1.rename(columns={lati_colname:'lati',long_colname:'long',zagl_colname:'zagl',
                              run_times_colname:'run_times',rec_is_agl_colname:'z_is_agl',
                              'receptor_zasl':'zasl','z_ail':'zail'}) #rename the columns
    df1 = df1[['run_times','lati','long','zagl','z_is_agl','zasl','zail']] #only get the columns we need

    #do some rounding so we don't have to write a bunch of digits
    df1['lati'] = df1['lati'].round(4)
    df1['long'] = df1['long'].round(4)
    df1['zagl'] = df1['zagl'].round(2)
    df1['run_times'] = df1['run_times'].round('S')

    #df1['run_times'] = df1['run_times'].dt.tz_localize(None)
    df1 = df1.dropna() #drop na values, usually where the sun is not up 
    df1 = df1.reset_index(drop=True) #reset the index, especially necessary in the case of multiindexing
    df1 = df1.reset_index() #reset it again so we can get a simulation id from the numerical index
    df1 = df1.rename(columns={'index':'sim_id'}) #rename the index column the sim id
    return df1

def format_datetime(year,month,day,hour,minute,second,tz='US/Mountain'):
    '''Formats an input datetime from input values and returns both a string, as well as a timezone aware object
    
    Args:
    year (int) : year of measurment
    month (int) : month of measurment
    day (int) : day of measurment
    hour (int) : hour of measurement
    minute (int) : minute of measurement
    second (float) : second of measurement
    tz (str) : timezone of measurement from the pytz.timezone available options (default = 'US/Mountain')

    Returns: 
    dt_str (str) : datetime of input represented as a string
    tz_dt (datetime.datetime object) : timezone aware datetime.datetime object
    '''

    dt_str = f'{year}-{month:02}-{day:02} {hour:02}:{minute:02}:{second}' #write the string
    dt = datetime.datetime.strptime(dt_str,'%Y-%m-%d %H:%M:%S.%f') #convert it to a datetime
    tz_dt = pytz.timezone(tz).localize(dt) #localize to the correct timezone
    return dt_str,tz_dt

def get_fulldaystr_from_oofname(oof_filename):
    '''Gets datetime strings spanning the entire day, based on an oof filename
    
    Args:
    oof_filename (str) : name of an oof file with format xxYYYYmmdd*.oof
    
    Returns:
    dt1_str (str) : datetime string of form "YYYY-mm-dd 00:00:00 (first second of day)
    dt2_str (str) : datetime string of form "YYYY-mm-dd 23:59:59 (last second of day)
    '''

    datestring = f'{oof_filename[2:6]}-{oof_filename[6:8]}-{oof_filename[8:10]}' #parse the date from the oof file
    dt1_str = f'{datestring} 00:00:00' #get the datetime string of the first time of the day
    dt2_str = f'{datestring} 23:59:59' #get the datetime string of the last time of the day
    return dt1_str,dt2_str

def haversine(lat1,lon1,lat2,lon2):
    '''Calculate the great circle distance between two points on the earth 
    
    Args:
    lat1 (float) : longitude of first point
    lon1 (float) : latitude of first point
    lat2 (float) : longitude of second point
    lon2 (float) : latitude of second point

    Returns:
    distance (float) : distance in meters along the great circle between the two points
    '''

    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r * 1000 #convert to meters

def get_nearest_from_grid(hrrr_grid_df,pt_lat,pt_lon,colname_to_extract='HGT_P0_L1_GLC0',lat_name='gridlat_0',lon_name='gridlon_0'):
    '''Input a lat/lon, return a value from a dataframe created from an xarray with lat/lon grid
    
    Args: 
    hrrr_grid_df (pd.DataFrame) : pandas dataframe, usually built using xarray.to_dataframe(), representing a grid of lat/lons and associated values
    pt_lat (float) : point of interest latitude
    pt_lon (float) : point of interest longitude
    colname_to_extract (str) : column name of the hrrr_grid_df holding the value we want to extract at the nearest lat/lon. Default "HGT_P0_L1_GLC0" which is surface height
    lat_name (str) : name of the latitude column (attribute) in the hrrr_grid_df
    lon_name (str) : name of the longitude column (attribute) in the hrrr_grid_df
    '''

    if (pd.isna(pt_lon))|(pd.isna(pt_lat)): #if the input point has a nan, return nan
        return np.nan
    df = hrrr_grid_df.loc[(hrrr_grid_df[lon_name]>=pt_lon-.1)&
                (hrrr_grid_df[lon_name]<=pt_lon+.1)&
                (hrrr_grid_df[lat_name]>=pt_lat-.1)&
                (hrrr_grid_df[lat_name]<=pt_lat+.1)] #filter df to 0.1 degrees around the point to speed up processs
    if len(df.dropna()) == 0: #if in creating the df, all the points were dropped, we're outside the bounds of the grid. Return nan
        #print('Point is outside the bounds of the HRRR grid')
        return np.nan
    df['dist'] = np.vectorize(haversine)(df[lat_name],df[lon_name],pt_lat,pt_lon) #add a distance column for each subpoint using haversine
    idx = df['dist'].idxmin() #find the minimum distance
    return df.loc[idx][colname_to_extract] #return the value requested

def load_singletime_hgtdf(inst_lat,inst_lon,inst_zasl,tz_dt,z_ail_list):
    '''Create a slant dataframe for a single datetime
    
    Args:
    inst_lat (float) : latitude of the instrument
    inst_lon (float) : longitude of the instrument
    inst_zasl (float) : elevation above sea level of the instrument, in meters
    tz_dt (datetime.datetime) : timezone-aware datetime of the measurment
    z_ail_list (list of floats/ints) : list of receptor z elevations above the instrument level (ail) in meters
    '''

    z_asl_list = [x+inst_zasl for x in z_ail_list] #use the instrument level to get the elevation of the receptor points above sea level
    pt_lats = [] #initialize a list of lats
    pt_lons = [] #intitialize a list of lons
    for z in z_ail_list: #loop through the list of z heights above the instrument level. This is the vertical component of the geometry, the rest comes from the sun position. 
        pt_lat,pt_lon = slant_lat_lon(inst_lat,inst_lon,tz_dt,z) #KEY FUNCTION: gets the lat/lon of a point along the slant column, z meters above the instrument, at the input datetime
        pt_lats.append(pt_lat) #append the lat of the receptor point
        pt_lons.append(pt_lon) #append the lon of the receptor point
    slant_df = pd.DataFrame({'z_ail':z_ail_list,'receptor_zasl':z_asl_list,'receptor_lat':pt_lats,'receptor_lon':pt_lons}) #create the dataframe of points along the slant column
    return slant_df

def slant_lat_lon(inst_lat,inst_lon,dt,z_above_inst):
    '''Gets the lat/lon coordinates of a slant column given instrument position, datetime, and desired z height above the instrument
    
    Args:
    inst_lat (float) : decimal latitude of the instrument
    inst_lon (float) : decimal longitude of the instrument
    dt (Timestamp) : datetime of the measurment
    z_above_inst (float) : z level above the instrument in meters
    
    Returns: 
    new_lat (float) : decimal latitude of the point on the solar slant column at the given z
    new_lon (float) : decimal longitude of the point on the solar slant column at the given z
    '''
    
    try:
        sol_zen_deg = 90-solar.get_altitude(inst_lat,inst_lon,dt) #tries to handle the datetime
    except Exception as e:
        #print(e) 
        dt = dt.to_pydatetime() #if it's a pandas timestamp, convert it to a datetime.datetime
        sol_zen_deg = 90-solar.get_altitude(inst_lat,inst_lon,dt) #the solar zenith angle (solar.get_altitude() gives the angle from horizontal, not zenith, so subtract from 90
    if sol_zen_deg>90: #when the solar zenith angle is greater than 90, the sun is below the horizon and the algorithm breaks down
        return np.nan,np.nan #so just return nans
    sol_zen_rad = np.deg2rad(sol_zen_deg) #convert to radians for use in the tangent function
    sol_azi_deg = solar.get_azimuth(inst_lat,inst_lon,dt) #get the solar azimuth
    arc_dist = z_above_inst * np.tan(sol_zen_rad) #get the horizontal distance given the height above the instrument using the correct geometry
    geod = Geodesic.WGS84 #set up the geodesic for dealing with earth being an ellipse
    new_point = geod.Direct(inst_lat,inst_lon,sol_azi_deg,arc_dist) #calculate the new point on earth's ellipsoid using initial lat/lon, azimuth (bearing) and distance
    new_lat = new_point['lat2'] #pull out and return the new point
    new_lon = new_point['lon2']
    #print(f'z={z_above_inst} || zenith_deg={sol_zen_deg} || azim_deg={sol_azi_deg} || dist={arc_dist} || newlat={new_lat} || newlong={new_lon}')
    return new_lat,new_lon

def add_sh_and_agl(slant_df,my_dem_handler):
    '''Add columns for the surface heights, receptor height above ground level, and boolean column if the receptor height is actually ABOVE the ground (nonnegative)
    
    Args:
    slant_df (pd.DataFrame) : pandas dataframe of slant data. Must have columns "receptor_lat", "receptor_lon", and "receptor_zasl"
    hrrr_grid_df (pd.DataFrame) : pandas dataframe of the hrrr grid for surface elevations (needs HGT_P0_L1_GLC0)
    
    Returns:
    slant_df (pd.DataFrame) : the same input dataframe with three new columns --
                              receptor_shasl = surface height at the receptor lat/lon in meters above sea level
                              receptor_zagl = height of the receptor above the ground level at its lat/lon
                              receptor_z_is_agl = boolean column where true means the receptor is actually above the ground
    '''
    print('adding surface and agl heights')
    slant_df['receptor_shasl'] = slant_df.apply(lambda row: my_dem_handler.get_nearest_elev(row['receptor_lat'],row['receptor_lon']),axis=1) #get the nearest surface height from the hrrr grid
    slant_df['receptor_zagl'] = slant_df.apply(lambda row: row['receptor_zasl'] - row['receptor_shasl'],axis = 1) #subtract the height of the receptor from the surface height
    slant_df['receptor_z_is_agl'] = slant_df['receptor_zagl'].gt(0) #add the boolean column for if the point is above the ground
    return slant_df

def pdcol_is_equal(pdcol):
    '''Checks if all of the values in a column of a dataframe are equal to one another
    
    Args: 
    pdcol (column of a pd dataframe)
    
    Returns:
    (bool) : true if all of the values in a column are equal, false if any are different
    '''

    a = pdcol.to_numpy()
    return (a[0]==a).all()

def create_dt_list(dt1, dt2, interval):
    '''Creates a list of datetime elements within the range subject to an input interval

    Args:
    dt1 (datetime.datetime): start datetime (can be tz-aware or naive)
    dt2 (datetime.datetime): end datetime (must match dt1's tz)
    interval (str): interval string like "1H", "2T" etc

    Returns:
    dt_list (list): list of datetimes at the input interval between dt1 and dt2 inclusive
    '''

    # If both are tz-aware, preserve timezone in range
    if dt1.tzinfo is not None and dt2.tzinfo is not None:
        dt_index = pd.date_range(dt1, dt2, freq=interval, tz=dt1.tzinfo)
    else:
        dt_index = pd.date_range(dt1, dt2, freq=interval)
    return list(dt_index)

def dtstr_to_dttz(dt_str,timezone):
    '''Gets a datetime from a string and timezone
    
    Args:
    dt_str (str) : string of style YYYY-mm-dd HH:MM:SS 
    timeszone (str) : string of the timezone, like "UTC" 

    Returns:
    dt (datetime.datetime) : a tz-aware datetime object
    '''
    dt = datetime.datetime.strptime(dt_str,'%Y-%m-%d %H:%M:%S')
    dt = pytz.timezone(timezone).localize(dt)
    return dt

def merge_oofdfs(oof_dfs,dropna=False):
    '''Function to merge oof dfs and add the instrument id as a suffix to each column name. Generally we use
    this when comparing two oof dfs, such as correcting one to another via an offset. 
    
    Args: 
    oof_dfs (dict): dictionary of oof dataframes, where the key is the instrument id (like 'ha') and the value is the dataframe
    dropna (bool): True if we want to drop na values (when joining, often there are many), False if not. Default False
    
    Returns:
    merged_df (pd.DataFrame): pandas dataframe of the merged oof dfs, with suffixes for instrument id added to each column
    '''

    inst_ids = oof_dfs.keys() #get the instrument ids
    dfs_for_merge = {} #initialize the dataframes for merging
    for inst_id in inst_ids: #loop through the instrument ids
        df = oof_dfs[inst_id].copy() #copy the dataframe for that instrument id
        for col in df.columns: #for each of the columns in the dataframe
            df = df.rename(columns={col:f'{col}_{inst_id}'}) #add the instrument id as a suffix to the original column name after a _
        dfs_for_merge[inst_id] = df #add this dataframe to the merge dict
    merged_df = pd.DataFrame() #initialize the merged dataframe
    for inst_id in inst_ids: #for all of the dataframes
        merged_df = pd.concat([merged_df,dfs_for_merge[inst_id]],axis = 1) #merge them into one by concatenating
    if dropna: #if we want to drop the na values,
        merged_df = merged_df.dropna() #do it
    return merged_df

def get_stilt_ncfiles(output_dir):
    by_id_fulldir = os.path.join(output_dir,'by-id')
    id_list = os.listdir(by_id_fulldir)
    #for id in id_list:
        # print(id)
        # try:
        #     print(f"{id}: {os.path.join(by_id_fulldir,id)/}")

def find_sbs_ranges(inst_details,inst_id1,inst_id2):
    inst_det_list1 = inst_details[inst_id1]
    inst_det_list2 = inst_details[inst_id2]
    sbs_details = {}
    for inst_det1 in inst_det_list1:
        for inst_det2 in inst_det_list2:
            if inst_det1['site'] == inst_det2['site']:
                site = inst_det1['site']
            else:
                continue
            dtr1 = inst_det1['dtr']
            dtr2 = inst_det2['dtr']
            sbs_dtr = dtr1.intersection(dtr2)
            if sbs_dtr is not None:
                try:
                    sbs_details[site].append(sbs_dtr)
                except KeyError:
                    sbs_details[site] = [sbs_dtr]
            
    return sbs_details

def find_sbs_ranges_inrange(inst_details,inst_id1,inst_id2,dtrange):
    sbs_details = find_sbs_ranges(inst_details,inst_id1,inst_id2)
    sub_site_details = {}
    for site in sbs_details.keys():
        for sbs_dtr in sbs_details[site]:
            intersection = sbs_dtr.intersection(dtrange)
            if intersection is not None:
                try:
                    sub_site_details[site].append(intersection)
                except KeyError:
                    sub_site_details[site] = [intersection]

    return sub_site_details

def get_surface_ak(ds,xgas_name):
    """ Gets the surface averaging kernel for a given xgas from the xarray dataset (loaded from the ggg .nc file)
    
    Args:
        ds (xarray.Dataset) : xarray dataset loaded from the ggg .nc file
        xgas_name (str) : name of the gas to get the surface ak for, like 'co2(ppm)' or 'ch4(ppm)'

    Returns:
        surface_ak_interp (xarray.DataArray) : xarray DataArray of the surface ak for the given gas, interpolated to the slant column values
    """
    airmass = ds['o2_7885_am_o2']
    xgas = ds[xgas_name]
    slant_xgas = xgas * airmass

    ak_surface = ds[f'ak_{xgas_name}'].isel(ak_altitude=0).values
    surface_interpolated_values = []
    slant_xgas_values = slant_xgas.values
    ak_slant_xgas_bin = ds[f'ak_slant_{xgas_name}_bin'].values

    for slant_value in slant_xgas_values:
        interpolated_surface_ak = np.interp(
            slant_value, #current slant value
            ak_slant_xgas_bin, #bin centers
            ak_surface, #ak values
        )
        surface_interpolated_values.append(interpolated_surface_ak)

    surface_ak_interp = xr.DataArray(
        surface_interpolated_values,
        dims='time',
        coords={'time':ds.time}
    )

    return surface_ak_interp

def add_rise_set(oof_df):
    '''Adds a column to the dataframe indicating if the sun is rising or setting at that time
    
    Args:
    oof_df (pd.DataFrame) : pandas dataframe of oof data, must have a column 'solzen(deg)' for the solar zenith angle
    
    Returns:
    out_oof_df (pd.DataFrame) : the same input dataframe with a new column 'rise_set' added, indicating if the sun is rising or setting
    '''
    
    out_oof_df = pd.DataFrame() #initialize the output dataframe
    oof_day_dfs = [part for _, part in oof_df.groupby(pd.Grouper(freq='1D')) if not part.empty] #parse into a list of daily dataframes
    for df in oof_day_dfs: #for each daily dataframe
        min_sza_idx = df['solzen(deg)'].idxmin() #find the sun's peak (min sza)
        df['rise_set'] = ['rise' if idx <= min_sza_idx else 'set' for idx in df.index] #add a column indicating if the sun is rising or setting (before or after peak)
        out_oof_df = pd.concat([out_oof_df,df]) #concatenate the daily dataframes into one

    return out_oof_df #return the concatenated dataframe

def copy_em27_oofs_to_singlefolder(existing_results_path,oof_destination_path):
    '''Copies oof files from the EM27 results path to a single directory
    
    Args:
    existing_results_path (str) : path to the results folder. Within this folder should be a 'daily' and further date subfolders.
    oof_destination_path (str) : path to the folder where the oof files will be copied
    '''

    files_to_transfer = []
    daily_results_folder = os.path.join(existing_results_path,'daily') 
    for datefolder in os.listdir(daily_results_folder):
        for file in os.listdir(os.path.join(daily_results_folder,datefolder)):
            if file.endswith('.vav.ada.aia.oof'):
                full_filepath = os.path.join(daily_results_folder,datefolder,file)
                files_to_transfer.append(full_filepath)
    print('Copying Files')
    for full_filepath in files_to_transfer:
        shutil.copy(full_filepath,oof_destination_path)

def div_by_ak(df,col_name,ak_col_name):
    out_df = df.copy()
    out_df[f'{col_name}_divak'] = out_df[col_name] / out_df[ak_col_name]
    return out_df

# Anomaly functions
def create_binned_summary(df,ak_df,sza_bin_size,gases):
    '''Creates a summary dataframe for binning values on sza for rising and setting sun. Used for getting "daily anomolies" per Wunch 2009
    
    Args:
    df (pd.DataFrame): pandas dataframe containing EM27 data
    sza_bin_size (int, float): size (in degrees) to make the solar zenith angle bins
    gases (list): list of strings corresponding to the species wanted. takes the mean of each species for the corresponding "rise" or "set for the sza bin
    
    Returns:
    binned_summary_df (pd.DataFrame): dataframe containing information about the sza binned data'''
    bins = np.arange(0,90,sza_bin_size) #create the bins
    df['sza_bin'] = pd.cut(df['solzen(deg)'],bins) #create a column in the dataframe indicating the bin that row belongs to
    grouped = df.groupby(['sza_bin','rise_set']) #group by the bin as well as rise_set so that they are two separate entities
    binned_summary = [] #initialize a list to store summary data
    for name, group in grouped:
        bin_dict = {} #initialize the binned group's data dict
        bin_dict['tstart'] = group.index[0] #start time of the bin
        bin_dict['tend'] = group.index[-1] #end time of the bin
        bin_dict['tmid'] = bin_dict['tstart']+(bin_dict['tend']-bin_dict['tstart'])/2 #middle time of the bin (can be used for plotting)
        bin_dict['sza_bin'] = name[0] #the sza bin itself
        bin_dict['nobs'] = len(group) #how many observations in that bin
        spec_bin_means = group.mean(numeric_only=True)[gases] #get the means of the species we want
        bin_dict.update({gas:spec_bin_means[gas] for gas in gases}) #add the means to the bin_dict
        bin_dict.update({f'{gas}_error':group.mean(numeric_only=True)[f'{gas}_error'] for gas in gases}) #add the std dev of the species to the bin_dict
        bin_dict.update({f'{gas}_std':group.std(numeric_only=True)[f'{gas}'] for gas in gases}) #add the std dev of the species to the bin_dict
        bin_dict['rise_set'] = name[1] #whether it is 'rise' or 'set'

        # Filter the averaging kernel DataFrame for the time range of the bin
        ak_filtered = ak_df[(ak_df.index >= bin_dict['tstart']) & (ak_df.index <= bin_dict['tend'])]
        if not ak_filtered.empty:
            for gas in gases:
                ak_col = f'{gas}_surf_ak'
                bin_dict[f'{gas}_surf_ak'] = ak_filtered[ak_col].mean()

        binned_summary.append(bin_dict) #append that group's info to the summary list
    binned_summary_df = pd.DataFrame(binned_summary)  #make the dataframe from the list of dicts
    binned_summary_df['sza_mid'] = binned_summary_df.apply(lambda row:row['sza_bin'].mid,axis = 1)
    return binned_summary_df

def daily_anomaly_creator(binned_summary_df,gases,co2_thresh):
    '''Create the daily anomoly
    
    Args:
    binned_summary_df (pd.DataFrame): created using create_binned_summary, contains daily summary information
    gases (list): list of the species names to use
    
    Returns:
    anom_df (pd.DataFrame): dataframe of the daily anomolies
    skipped_df (pd.DataFrame): dataframe containing information about bins that were skipped and why
    '''

    bin_grouped = binned_summary_df.groupby('sza_bin') #group by sza bin
    #initialize the data lists
    anom_list = []
    skipped_list = []
    for name,group in bin_grouped:
        if len(group)>2: #make sure there's not more than two rows -- should just be one rise and one set for that sza bin
            raise Exception('grouped df greater than 2 -- investigate') 
        if not all(item in group['rise_set'].values for item in ['rise', 'set']): #check that exactly one rise and one set rows exist in the df
            skipped_list.append(dict(skipmode = 'no_match_sza', #document if so
                                        sza_bin = name,
                                        rise_set = group['rise_set'].unique()))
            continue #if there aren't a rise and set, we can't do the anomoly, so just go to the next grouping
        if (group['nobs'].max()>(2*group['nobs'].min())): #check that there aren't more that 2x the number of observations for "rise" compared to set (or vice versa)
            skipped_list.append(dict(skipmode = 'nobs',
                                        sza_bin = name)) #ifso, document and continue
            continue
        rise_row = group.loc[group['rise_set']=='rise'].squeeze() #get the rise data (squeeze gets the value)
        set_row = group.loc[group['rise_set']=='set'].squeeze() #same with set
        anom_dict = {f'{gas}_anom':(set_row[gas] - rise_row[gas]) for gas in gases} #subtract rise from set for that sza, for each species in the list
        anom_dict.update({'sza_bin':name}) #update the dict with the sza bin
        anom_dict.update({f'{gas}_error' : np.mean(group[f'{gas}_error']) for gas in gases}) #add the error (mean of the two)
        anom_dict.update({f'{gas}_std' : np.mean(group[f'{gas}_std']) for gas in gases})
        anom_dict.update({f'{gas}_surf_ak' : np.mean(group[f'{gas}_surf_ak']) for gas in gases})
        anom_list.append(anom_dict) #append it to the list
        
    anom_df = pd.DataFrame(anom_list) #create the dataframe for the anomolie
    if len(anom_df) > 0: #if there are entries in the anom df, add a sza midpoint for plotting
        anom_df['sza_mid'] = anom_df.apply(lambda row: row['sza_bin'].mid,axis = 1)
        for gas in gases:
            anom_df = div_by_ak(anom_df,f'{gas}_anom',f'{gas}_surf_ak')
            anom_df = div_by_ak(anom_df,f'{gas}_error',f'{gas}_surf_ak')
            anom_df = div_by_ak(anom_df,f'{gas}_std',f'{gas}_surf_ak')
        anom_df['co2_above_thresh']  = (anom_df['xco2(ppm)_anom'].max()- anom_df['xco2(ppm)_anom'].min())>co2_thresh
    skipped_df = pd.DataFrame(skipped_list) #create the dataframe for why some sza's may have been skipped
    return anom_df, skipped_df


###################################################################################################################################
# Define Classes
###################################################################################################################################
class oof_manager:
    '''Class to manage getting data from oof files'''

    def __init__(self,oof_data_folder,timezone):
        '''
        Args: 
        oof_data_folder (str) : path to the folder where oof data is stored
        timezone (str) : timezone for the measurments
        '''
        self.oof_data_folder = oof_data_folder
        self.timezone = timezone

    def load_oof_df_inrange(self,dt1,dt2,filter_flag_0=False,print_out=False,cols_to_load=None):
        '''Loads a dataframe from an oof file for datetimes between the input values
        
        Args:
        dt1_str (str) : string for the start time of the desired range of form "YYYY-mm-dd HH:MM:SS" 
        dt2_str (str) : string for the end time of the desired range of form "YYYY-mm-dd HH:MM:SS" 
        oof_filename (str) : name of the oof file to load
        filter_flag_0 (bool) : True will filter the dataframe to rows where the flag column is 0 (good data), false returns all the data
        print_out (bool) : Will print a message telling the user that they are loading a certain oof file. Default False. 
        cols_to_load (list) : List of strings that are the names of the oof data columns to load. Default is None, which loads all of the columns. 

        Returns:
        df (pd.DataFrame) : pandas dataframe loaded from the oof files, formatted date, and column names       
        '''
        if type(dt1) == str:
            dt1 = self.tzdt_from_str(dt1)
            dt2 = self.tzdt_from_str(dt2)
        oof_files_inrange = self.get_oof_in_range(dt1,dt2)
        full_df = pd.DataFrame()
        for oof_filename in oof_files_inrange:
            if print_out:
                print(f'Loading {oof_filename}')
            df = self.df_from_oof(oof_filename,fullformat = True, filter_flag_0 = filter_flag_0, cols_to_load=cols_to_load) #load the oof file to a dataframe
            #df = self.df_dt_formatter(df) #format the dataframe to the correct datetime and column name formats
            df = df.loc[(df.index>=dt1)&(df.index<=dt2)] #filter the dataframe between the input datetimes
            #if filter_flag_0: #if we want to filter by flag
            #    df = df.loc[df['flag'] == 0] #then do it!
            full_df = pd.concat([full_df,df])
        return full_df

    def df_from_oof(self,filename,fullformat = False,filter_flag_0 = False,cols_to_load=None):
        '''Load a dataframe from an oof file
        
        Args:
        filename (str) : name of the oof file (not the full path)
        fullformat (bool) : if you want to do the full format
        filter_flag_0 (bool) : if you want to only get the 0 flags (good data), set to True
        cols_to_load (list) : list of strings of the oof columns you want to load. Default None which loads all of the columns
        
        Returns:
        df (pd.DataFrame) : a pandas dataframe loaded from the em27 oof file with applicable columns added/renamed
        '''

        oof_full_filepath = os.path.join(self.oof_data_folder,filename) #get the full filepath using the class' folder path
        header = self.read_oof_header_line(oof_full_filepath)
        if cols_to_load == None: #if use_cols is none, we load all of the columns into the dataframe
            df = pd.read_csv(oof_full_filepath,
                            header = header,
                            sep='\s+',
                            skip_blank_lines=False) #read it as a csv, parse the header
        else:
            must_have_cols = ['flag','year','day','hour','lat(deg)','long(deg)','zobs(km)'] #we basically always need these columns
            usecols = cols_to_load.copy() #copy the cols to load so it doesn't alter the input list (we often use "specs" or simlar)
            for mhc in must_have_cols: #loop through the must haves
                if mhc not in cols_to_load: #if they aren't in the columns to load
                    usecols.append(mhc) #add them 

            df = pd.read_csv(oof_full_filepath, #now load the dataframe with the specific columns defined
                header = header,
                sep='\s+',
                skip_blank_lines=False,
                usecols = usecols) #read it as a csv, parse the header
                
        df['inst_zasl'] = df['zobs(km)']*1000 #add the instrument z elevation in meters above sea level (instead of km)
        df['inst_lat'] = df['lat(deg)'] #rename the inst lat column
        df['inst_lon'] = df['long(deg)'] #rename the inst lon column 
        if fullformat:
            df = self.df_dt_formatter(df)
        if filter_flag_0:
            df = df.loc[df['flag']==0]
        return df

    def tzdt_from_str(self,dt_str):
        '''Apply the inherent timezone of the class to an input datetime string
        
        Args:
        dt_str (str) : datetime string of form "YYYY-mm-dd HH:MM:SS" 
        
        Returns:
        dt (datetime.datetime) : timezone aware datetime object, with timezone determined by the class
        '''

        dt = datetime.datetime.strptime(dt_str,'%Y-%m-%d %H:%M:%S') #create the datetime
        dt = pytz.timezone(self.timezone).localize(dt) #apply the timezone
        return dt

    def read_oof_header_line(self,full_file_path):
        '''Reads and parses the header line of an oof file
        
        Args: 
        full_file_path (str) : full path to an oof file we want to read
        
        Returns:
        header (list) : list of column names to use in the header 
        '''

        with open(full_file_path) as f: #open the file
            line1 = f.readline() #read the first line
        header = int(line1.split()[0])-1 #plit the file and get the header
        return header

    def parse_oof_dt(self,year,doy,hr_dec):
        '''Get a real datetime from an oof style datetime definition
        
        Args:
        year (int) : year
        doy (int) : day of the year 
        hr_dec (float) : decimal hour of the day
        
        Returns:
        dt (pandas.datetime) : pandas datetime object gleaned from the inputs
        '''

        dt = pd.to_datetime(f'{int(year)} {int(doy)}',format='%Y %j') + datetime.timedelta(seconds = hr_dec*3600)
        return dt

    def df_dt_formatter(self,df):
        '''Format a loaded oof dataframe to have the correct datetime as an index

        Assumes that the oof timestamps are in UTC
        
        Args: 
        df (pd.DataFrame) : dataframe loaded using df_from_oof() 

        Returns:
        df (pd.DataFrame) : reformatted dataframe with datetime as the index, and converted to a timezone aware object. 
        '''

        df['dt'] = np.vectorize(self.parse_oof_dt)(df['year'],df['day'],df['hour']) #set the datetime column by parsing the year, day and hour columns
        df = df.set_index('dt',drop=True).sort_index() #set dt as the index
        df.index = df.index.tz_localize('UTC').tz_convert(self.timezone) #localize and convert the timezone
        return df

    def get_sorted_oof(self):
        '''Get a list of oof files in the oof data folder, sorted so they are in chron order
        
        Returns:
        files (list) : list of files ending in oof in the data folder
        '''

        files = [] #initialize the list
        for file in sorted(os.listdir(self.oof_data_folder)): #loop through the sorted filenames in the oof data folder
            if file.endswith('oof'): #if the file ends in oof
                files.append(file) #add it to the list
        return files

    def get_oof_in_range(self,dt1,dt2):
        '''Finds the oof files in the data folder that fall between two input datetimes
        
        Args:
        dt1 (str or datetime.datetime) : start datetime of the interval we want to find files within
        dt2 (str or datetime.datetime) : end datetime of the interfal we want to find files within
        
        Returns:
        files in range (list) : list of oof filenames that fall within the datetime range input
        '''
        dt1 = dt1 - datetime.timedelta(days=1) #sometimes with UTC there are values in the previous day's oof file, so start one behind to check
        daystrings_in_range = [] #initialize the day strings in the range
        delta_days = dt2.date()-dt1.date() #get the number of days delta between the end and the start
        for i in range(delta_days.days +1): #loop through that number of days 
            day = dt1.date() + datetime.timedelta(days=i) #get the day by incrementing by i (how many days past the start)
            daystrings_in_range.append(day.strftime('%Y%m%d')) #append a string of the date (YYYYmmdd) to match with filenames

        files_in_range = [] #initilize the filenames that will be in the range
        for file in self.get_sorted_oof(): #loop through the sorted oof files in the data folder
            for daystring_in_range in daystrings_in_range: # loop through the daystrings that are in the range
                if daystring_in_range in file: #if the daystring is in the filename, 
                    files_in_range.append(file) #append it. Otherwise keep going
        
        return files_in_range

    def date_from_oof(self,oof_filename):
        '''Strips the date from an oof filename
        
        Args: 
        oof_filename (str)

        Returns:
        date (datetime.datetime.date) : date gained from the oof filename
        '''

        try:
            datestring = oof_filename.split('.')[0][2:] #split the oof_filename on . and remove the two letter identifier 
            date = datetime.datetime.strptime(datestring,"%Y%m%d").date() #convert to a date
            return date
        except:
            raise Exception(f'Error in getting datestring from {oof_filename}')

    def get_inrange_dates(self,dt1,dt2):
        '''Gets a range of dates between an input datetime range
        
        Args:
        dt1 (datetime.datetime) : start datetime
        dt2 (datetime.datetime) : end datetime
        
        Returns:
        dates_in_range (list) : list of dates within the datetime range
        '''

        files_in_range = self.get_oof_in_range(dt1,dt2) #find the files in the range
        dates_in_range = [] #initialize the dates list
        for oof_filename in files_in_range: #loop through the files in the range
            inrange_date = self.date_from_oof(oof_filename) #grab the date
            dates_in_range.append(inrange_date) #and append it
        return dates_in_range

    def check_get_loc(self,oof_df):
        '''Checks and gets the location of the instrument from the oof file
        TODO: This will break if the location moves during data collection or between days. This could become an issue if data was collected
        during one day and went past midnight UTC, then moved to a differnt location the next day. The oof_df in this case for the secnod day
        would include some data from the first data colleciton session in the early UTC hours, before moveing. 

        Args: 
        oof_df (pd.DataFrame) : dataframe of oof values
        
        Returns: 
        inst_lat (float) : instrument latitude
        inst_lon (float) : instrument longitude
        inst_zasl (float) : instrument elevation above sea level in meters        
        '''

        cols_to_check = ['inst_lat','inst_lon','inst_zasl']
        for col in cols_to_check:
            if not pdcol_is_equal(oof_df[col]):
                raise Exception('{col} is not the same for the entire oof_df. This is an edge case.')
        #If we make it through the above, we can pull the values from the dataframe at the 0th index because they are all the same
        inst_lat = oof_df.iloc[0]['inst_lat']
        inst_lon = oof_df.iloc[0]['inst_lon']
        inst_zasl = oof_df.iloc[0]['inst_zasl']
        return inst_lat,inst_lon,inst_zasl   
    
class ground_slant_handler:
    '''Class to handle getting slant column receptors'''

    def __init__(self,inst_lat,inst_lon,inst_zasl,z_ail_list):#,hrrr_subset_path,hrrr_subset_datestr = '2023-01-01'):
        '''
        Args: 
        inst_lat (float) : latitude of instrument
        inst_lon (float) : longitude of instrument
        inst_zasl (float) : elevation of instrument above sea level in meters
        z_ail_list (list) : a list of elevations (in meters) above the instrument level at which to place receptors along the slant column
        hrrr_subset_path (str) : path to where the subset hrrr file should be stored
        hrrr_subset_datestr (str) : string of the date from which we want to pull the hrrr surface data
        '''

        self.inst_lat = inst_lat
        self.inst_lon = inst_lon
        self.inst_zasl = inst_zasl
        self.z_ail_list = z_ail_list
        #self.hrrr_subset_path = hrrr_subset_path
        #self.hrrr_subset_datestr = hrrr_subset_datestr

    def create_initial_slantdf(self,dt_list):
        '''Creates the initial slant dataframe. Will not include any surface elevation data, but gets the receptors in the correct lat/lon/zasl  for the give time periods

        Args:
        dt_list (list) : list of datetimes representing the times at which we want receptors to appear in the dataframe

        Returns:
        multi_df (pd.DataFrame) : a pandas dataframe with multiindex. Level 0 is the datetime, level 1 is the z elevation above instrument level
                                  other columns include the receptor lat, lon, zasl along the slant column. 

        '''
        combined_tuples = list(itertools.product(dt_list,self.z_ail_list)) #create a combined tuple for creating the multiindex, with item 0=datetime, item 1=z_ail
        #initialize a bunch of lists to build the dataframe
        receptor_lats = []
        receptor_lons = []
        receptor_zasls = []

        print(f'Adding receptor lat/lons along the slant column')
        i=1
        for dt,zail in combined_tuples: #loop through the datetime, zail tuples
            i+=1
            #Get the slant column for each of those points
            receptor_lat,receptor_lon = slant_lat_lon(self.inst_lat,self.inst_lon,dt,zail)
            receptor_zasl = zail+self.inst_zasl #add the elevation above sea level by adding above instrument level to the instrument elevation above sea level

            #Append all of the calculated or pulled values to the preallocated lists
            receptor_lats.append(receptor_lat)
            receptor_lons.append(receptor_lon)
            receptor_zasls.append(receptor_zasl)

        multi_df = pd.DataFrame(index = pd.MultiIndex.from_tuples(combined_tuples,names=['dt','z_ail'])) #create the multiindexed dataframe, using the combined tuples
        
        #populate the dataframe with the values calculated above
        multi_df['inst_lat'] = self.inst_lat 
        multi_df['inst_lon'] = self.inst_lon
        multi_df['inst_zasl'] = self.inst_zasl
        multi_df['receptor_lat'] = receptor_lats
        multi_df['receptor_lon'] = receptor_lons
        multi_df['receptor_zasl'] = receptor_zasls
        return multi_df

    def run_slant_at_intervals(self,dt1,dt2,my_dem_handler,interval='1h'):
        '''Gets a slant dataframe given a datetime range and interval
        
        Args:
        dt1 (datetime.datetime) : start datetime
        dt2 (datetime.datetime) : end datetime
        interval (str) : string of frequency type like default ("1H") or like "2T", "10S" etc
        
        Returns:
        multi_df (pd.DataFrame) : pandas dataframe with multiindex. Level 0 is the datetime, level 1 is the zail. Columns include
                                  the receptor lat, long, zasl, as well as the surface heights and zagl for stilt
        '''

        #for hrrr
        # try:
        #     self.hrrr_elev_df #if the hrrr surface height elevation exists, just keep going
        # except:
        #     self.load_hrrr_surf_hgts() #if it doesn't exist yet, load it
 
        dt_list = create_dt_list(dt1,dt2,interval) #create the dt list based on the range and interval
        multi_df = self.create_initial_slantdf(dt_list) #create the multidf 

        print('Adding surface height and receptor elevation above ground level')
        multi_df = add_sh_and_agl(multi_df,my_dem_handler) #Add the receptor surface heights and elevations above ground level
        
        if len(multi_df.dropna()) == 0:
            print('There are no receptors in the slant column. This often happens when (1) the time range defined in the config does not include any "sunlight" hours, or (2)\
                  the defined DEM does not cover the region of interest. Check the time range and the DEM fname in the input configs file.')
            raise Exception('No receptors in the slant column.')

        return multi_df

    def load_hrrr_surf_hgts(self):
        '''
        ***This stuff is depricated as of now, using dem_handler
        Loads the surface height dataframe, or downloads then loads if it doesn't exist yet
        
        Returns: 
        hrrr_elev_xarr_ds (xarray.dataset) : xarray dataset from a grib2 file loaded from hrrr
        hrrr_elev_df (pd.DataFrame) : pandas dataframe which is just the xarry converted to a dataframe
        '''

        hrrr_subset_datefolder = os.path.join(self.hrrr_subset_path,'hrrr',f'{self.hrrr_subset_datestr[0:4]}{self.hrrr_subset_datestr[5:7]}{self.hrrr_subset_datestr[8:10]}') #finds the hrrr datafolder (herbie creates a date subfolder and puts it in there)
        try: #try to list the files in the datafolder
            files = os.listdir(hrrr_subset_datefolder)
        except FileNotFoundError: #if there isn't a folder, there wasn't a hrrr subset grib2 file downloaded, so download it
            print(f'No subset data in the date given. Running retrieve_hrrr_subset to get the data for {self.hrrr_subset_datestr}.')
            self.retrieve_hrrr_subset() #retrieve the hrrr surface height grib2 subset for the day self.hrrr_subset_datestr
            files = os.listdir(hrrr_subset_datefolder) #list the files in the hrrr subset folder
        if len(files)>1: #if there are more than one file in this folder, it gets confused, should only have one. This could be a bug down the line
            raise Exception(f'Multiple subset files in {hrrr_subset_datefolder}')
        else: #if noth though
            hrrr_subset_full_filename = os.path.join(hrrr_subset_datefolder,files[0]) #get the full filename with the (singular) file in the full folder path 

        self.hrrr_elev_xarr_ds = xr.open_dataset(hrrr_subset_full_filename,engine='pynio') #load the hrrr grib2 file as an xarray dataset
        self.hrrr_elev_df = self.hrrr_elev_xarr_ds['HGT_P0_L1_GLC0'].to_dataframe().reset_index() #convert it to a dataframe
        return self.hrrr_elev_xarr_ds,self.hrrr_elev_df

    def retrieve_hrrr_subset(self):
        '''
        ***This stuff is depricated as of now, using dem_handler
        Gets a hrrr subset for surface height
        
        Doesn't return anythin, but uses the hrrr_subset_datestring to retrieve the correct subset using herbie
        '''
        H = Herbie(self.hrrr_subset_datestr,model='hrrr',product='sfc',fxx=0,save_dir=f'{self.hrrr_subset_path}') #setup the herbie subset
        H.download('HGT')   #download the height dataset

class DEM_handler:
    '''Class to handle DEMs... for now'''
    def __init__(self,dem_folder,dem_fname,dem_typeid):
        '''
        Args:
        dem_folder (str) : path where the DEM is stored
        dem_fname (str) : name of the DEM file
        dem_typeid (str) : right now, only functinality for 'aster'. Could use this to add ability to do other DEMS
        '''
        self.dem_folder = dem_folder
        self.dem_fname = dem_fname
        self.dem_typeid = dem_typeid
    
    def define_dem_ds(self):
        '''Defines the xarray dataset for the DEM
        The DEM xarray dataset can be defined without loading the whole thing in memory
        It also defines some other variables that are important based on the dem_typeid
        '''
        if self.dem_typeid == 'aster': 
            self.dem_dataname = 'ASTER_GDEM_DEM' #name of the piece of DEM data we want (in this case this is the surface elevation)
            self.dem_lonname = 'lon' #name of the longitude dimension
            self.dem_latname = 'lat' #name of the latitude dimension
            self.bound_box_deg = 0.01 #size of the bounding box when loading sliced dataarrays around a point. Because this one is fine scale, this is small.
            #Below load the dataset, but *I don't think* into memory. Some other minor specifications for different DEMS may be needed
            # as here we want to drop the "time" dimension as there is only one and it gets in the way 
            self.dem_ds = xr.open_dataset(os.path.join(self.dem_folder,self.dem_fname)).isel(time=0,drop=True) 
        else:
            raise Exception(f'DEM Type ID {self.dem_typeid} is not recognized')
    
    def get_sub_dem_df(self,pt_lat,pt_lon):
        '''Loads a dataframe representing a slice of the dataset around a point

        Args:
        pt_lat (float) : latitude of point around which to load
        pt_lon (float) : lontitude of a point around which to laod

        Returns:
        dem_df (pd.DataFrame) : Dataframe with lat, lon and the dem_dataname sliced around a point with a box the size of self.bound_box_deg
        '''
        try: 
            self.dem_ds #if the dataset doesn't exist 
        except: #load it
            print('No DEM dataset defined....defining.')
            self.define_dem_ds()
        #below is the slicing and loading into memory from the dataset, on a box the bound_box_deg*2 around the input point
        dem_da = self.dem_ds[self.dem_dataname].sel({self.dem_latname:slice(pt_lat+self.bound_box_deg,pt_lat-self.bound_box_deg),
                                                     self.dem_lonname:slice(pt_lon-self.bound_box_deg,pt_lon+self.bound_box_deg)}).load()
        dem_df = dem_da.to_dataframe().reset_index() #make it a dataframe
        return dem_df
    
    def get_nearest_elev(self,pt_lat,pt_lon):
        '''Gets the nearest elevation to an input point based on the DEM
        
        Args:
        pt_lat (float) : latitude of a point to get the nearest elevation at
        pt_lon (float) : longitude of a point to get the nearest elevation at
        
        Returns:
        surface_height (float) : value of the surface height at the nearest grid cell in the dem 
        '''
        dem_df = self.get_sub_dem_df(pt_lat,pt_lon) #get the df
        if len(dem_df)==0: #if there is no df, we're outsdie the domain of the DEM, so return nan
            #print('point is outside the DEMs range')
            return np.nan
        dem_df['dist'] = np.vectorize(haversine)(dem_df[self.dem_latname],dem_df[self.dem_lonname],pt_lat,pt_lon) #add a distance column for each subpoint using haversine
        idx = dem_df['dist'].idxmin() #find the minimum distance
        surface_height = dem_df.loc[idx][self.dem_dataname] #return the value requested
        return surface_height


class SlurmHandler:
    '''This class is for creating, adding to, and submitting a slurm script that can be submitted with sbatch'''

    def __init__(self,configs,custom_submit_name = None):
        '''
        Args:
        configs (obj of type StiltConfig) : configurations from a config json file to use 
        custom_submit_name (str) : if you would like a custom job submission name, define it here. Will default None to 'submit.sh'
        '''
        self.configs = configs #grabs everything from the configs
        if custom_submit_name is None: #default setting
            custom_submit_name = 'submit.sh'
        self.full_filepath = os.path.join(self.configs.folder_paths['slurm_folder'],'jobs',custom_submit_name) #define the full filepath of the submit fle
    
    def stilt_setup(self):
        '''Function to setup the initial lines for a set of STILT runs'''

        header = self.create_slurm_header() #create the header using the configs
        self.write_as_new_file(header) #write the header to a new file -- this will overwrite the current self.full_filepath
        self.append_to_file('SECONDS=0') #add a line initializeing "seconds" so we can display time it took to run in the output
    
    def add_stilt_run(self,stilt_name,run_stilt_fname='ac_run_stilt.r'):
        '''Adds the lines necessary to call STILT in the submit script located at self.full_filepath
        
        Args:
        stilt_name (str) : name of the stilt project (within configs.folder_paths['stilt_folder']) to be run
        run_stilt_fname (str) : name of the run_stilt file in stilt_name/r/, defaults to "ac_run_stilt.r" which is the default for stilt_setup.py
        '''
        self.add_echo_line('\n-----------------------------\n') #demarc between stilt runs
        slurm_line = f"Rscript {os.path.join(self.configs.folder_paths['stilt_folder'],stilt_name,'r',run_stilt_fname)}" #create the correct R call to the slurm script
        self.add_echo_line(slurm_line) # add a line that will echo the Rscript call to the output
        self.append_to_file(slurm_line) #actually append the Rscript line to be run
        self.echo_elapsed_seconds() #echo to the output how many seconds have passed since last call
        self.append_to_file('SECONDS=0') #reset seconds for the next elapsed time

    def submit_sbatch(self):
        '''Submits the sbatch script at self.full_filepath'''

        subprocess.call(['sbatch', self.full_filepath]) #do the call

    def create_slurm_header(self,shebang = '#!/bin/bash'):
        '''Creates the header for a submit file that can be read and submitted using sbatch
        
        Args:
        shebang (str) : the shebang to go at the beginning of the submit file, defaults to bash '!#/bin/bash'

        Returns:
        header (str) : a string, joined by newlines, that is the header for the submit file
        '''

        header_lines = [] #initialize a list of lines
        header_lines.append(shebang) #the first line should be the shebang
        for key,value in self.configs.slurm_options.items(): #loop through all of the "slurm_options" in the configs
            header_lines.append(f"#SBATCH --{key}={value}") #append the slurm options with the sbatch prefix needed for slurm
        log_path = os.path.join(self.configs.folder_paths['slurm_folder'],'logs',"%A.out") #define path of the log file TODO make it something better than just the job number %A...
        header_lines.append(f"#SBATCH -o {log_path}") #append the log  path
        header_lines.append('')  #append a blank for an extra line
        header = '\n'.join(header_lines) #join with newlines to create the header
        return header

    def add_echo_line(self,text_to_echo):
        '''Adds a line of text that we want to echo from the submit file to the stdout
        
        Args:
        text_to_echo (str) : what should be echoed'''

        self.append_to_file(f'echo "{text_to_echo}"') #append the echo line

    def echo_elapsed_seconds(self):
        '''Echo the amount of time sense the last $SECONDS=0 call to the stdout'''

        self.add_echo_line("Time since last = $SECONDS seconds")

    def append_to_file(self,text):
        '''Append a line of text to the submit file
        
        Args:
        text (str) : the text to append to the file
        '''

        with open(self.full_filepath,'a') as f: #open with append mode
            f.write(text+'\n') #add the text and a newline

    def write_as_new_file(self,text): 
        '''Overwrite the existing full_filepath and create a new file with text as an input
        
        Args:
        text (str) : the text to go at the top of the new file
        '''

        with open(self.full_filepath,'w') as f: #open under write mode
            f.write(text+'\n') #write the text and a new line

class StiltReceptors:
    '''A class to handle writing and loading stilt receptor files'''

    def __init__(self,configs,dt1=None,dt2=None,path=None,full_filepath=None):
        '''Initialize the class with configs as the necessary argument
        
        Args:
        configs (obj, StiltConfig) : configuration parameters scraped from the input config file
        dt1 (datetime.datetime) : datetime object for use in naming. Necessary when creating a new receptor csv. Defaults none for loading
        dt2 (datetime.datetime) : datetime object for use in naming. Necessary when creating a new receptor csv. Defaults none for loading
        path (str) : path to where either the receptor file should be written, or read from. Defaults none and set to tmp_folder/receptors/column_type
        full_filepath (str) : if you want to give the full filepath directly, can do that
        '''

        self.configs = configs 
        self.dt1 = dt1
        self.dt2 = dt2
        if path is None:
            path = os.path.join(self.configs.folder_paths['tmp_folder'],'receptors',self.configs.column_type) #get the path, including the column type, where receptor csv will be stored
        if not os.path.isdir(path):
            raise Exception(f'Invalid path {path}, nothin there.')
        
        if full_filepath is not None: #If the user input the full filepath
            self.full_filepath = full_filepath #set it and be done
        else: #otherwise, either find it or create it based on datetime values
            if dt1 is None: #if the datetime is none:
                fname = self.find_fname(path) #we need to find the fname in the path
            else: #if the datetime is there
                fname = self.create_fname() #we will be creating an fname
            self.full_filepath = os.path.join(path,fname) #define the full filepath

    def find_fname(self,path):
        '''Function to find a receptor filename in the path. A little kludgy now because it only works if theres just 1 csv in the path
        
        Args:
        path (str) : where to look for receptor files
        '''

        fnames = os.listdir(path) #get all the files in the path
        fnames = [f for f in fnames if f.endswith('csv')]  #only get the ones that end with csv
        if len(fnames) > 1: #if there are multiple files in the path
            raise Exception('Havent dealt with this case yet of multiple rec files in one folder')
        elif len(fnames) == 0:
            raise Exception(f'No csv files in {path}')
        else:
            return fnames[0]

    def create_fname(self):
        '''Defines the name of a receptor file based on the datetime range 
        
        Returns:
        fname (str) : filename based on the date and datetime range of the class
        '''
        if self.dt1 is None:
            raise Exception('You must initialize this class with dt1 and dt2 in order to create a new receptor file.')
        date = self.dt1.strftime('%Y%m%d') #grab the date of the dt1
        t1 = self.dt1.strftime('%H%M%S') #grab the start time
        t2 = self.dt2.strftime('%H%M%S') #grab the end time
        fname = f'{date}_{t1}_{t2}.csv' #define the filename as YYYYmmdd_HHMMSS_HHMMSS.csv
        return fname
    
    #Below are used for creating receptor files
    def create_for_stilt(self):
        '''The initialization of a receptor file to be used in stilt. Will overwrite anything with the self.full_filepath in favor of this call'''

        header = self.receptor_header()
        self.create_overwrite(header)

    def receptor_header(self):
        '''Write a header for to receptor file 
        
        Args:
        dt1 (datetime.datetime) : start datetime
        dt2 (datetime.datetime) : end datetime

        Returns:
        header (str) : the header text
        '''

        sha = get_git_hash(self.configs.folder_paths['Atmos_Column_folder'])
        header_lines = [] #initialize the header lines
        header_lines.append(f'Receptor file created using atmos_column.create_receptors, git hash:{sha}')
        header_lines.append(f'Column type:{self.configs.column_type}') #like the column type
        header_lines.append(f'Instrument Location:{self.configs.inst_lat},{self.configs.inst_lon},{self.configs.inst_zasl}masl')#the instrument info
        header_lines.append(f"Created at:{datetime.datetime.now(tz=datetime.UTC)}") #when the code was run
        header_lines.append(f"Data date1:{self.dt1.strftime('%Y%m%d')}") #the date of the data
        header_lines.append(f"Datetime range:{self.dt1},{self.dt2}") #and the range    
        header_lines.append('') #add a blank to get the last newline    
        header = '\n'.join(header_lines) #join the list on newlines
        return header

    def create_overwrite(self,text):
        '''Creates (if no file exists) or overwrites an existing file at self.full_filepath 
        
        Args:
        text (str) : the text to write at the top of the file'''

        with open(self.full_filepath, 'w') as f: #open the file in write mode 
            f.write(text + '\n') #write the text and a new line

    def append_text(self,text):
        '''Appends text to self.full_filepath
        
        Args:
        text (str) : the text to append
        '''

        with open(self.full_filepath,'a') as f: #open the file in append mode
            f.write(text + 'n') #write the text and a new line

    def append_df(self,df,index=False):
        '''Appends a pandas dataframe to self.full_filename as a csv
        
        Args:
        df (pd.DataFrame) : pandas dataframe in the "receptor" style
        index (bool) : if you want to write the index to the csv, default false
        '''

        df.to_csv(self.full_filepath,mode = 'a',index=index) #append the receptor dataframe to the created receptor csv with header. 

    #Below are used for reading/loading receptor files
    def load_receptors(self):
        '''Main method for loading a receptor file and the associated metadata, and saving to this class'''

        self.parse_rec_header() #parse the header and save the metadata to the calss
        self.rec_df = self.read_rec_csv() #read the csv file in as a df and save it to the class as rec_df
        self.split_dfs = self.split_recdf_bytime() #split the dfs into a list of dfs on time for easier usage

    def parse_rec_header(self):
        '''Read the header of the receptor file and store the data in the class'''

        with open(self.full_filepath) as f: #open the file
            header_lines = [] #initialize a list of the header lines
            line = ' ' #make line a space to get into the while loop
            while line != '': #the header should be followed by a blank line. stop after we read that
                line = f.readline().strip() #read the line and strip the newline character
                header_lines.append(line) #append the line to the header_lines list

        for line in header_lines: #loop through the header lines
            if line.split(':')[0] == 'Instrument Location': #ge the instrument location
                inst_loc_vals = line.split(':')[-1]
                self.inst_lat = float(inst_loc_vals.split(',')[0].strip())
                self.inst_lon = float(inst_loc_vals.split(',')[1].strip())
                self.inst_zasl = float(inst_loc_vals.split(',')[2].strip('masl'))
            if line.split(':')[0] == 'Datetime range': #get the datetime range
                inst_dt_vals = line.split('Datetime range:')[-1]
                self.dt_range_strs = [inst_dt_vals.split(',')[0],inst_dt_vals.split(',')[1]]
                self.dt1 = datetime.datetime.strptime(self.dt_range_strs[0],'%Y-%m-%d %H:%M:%S%z')
                self.dt2 = datetime.datetime.strptime(self.dt_range_strs[1],'%Y-%m-%d %H:%M:%S%z')
            if line.split(':')[0] == 'Data date':
                self.data_datestr = line.split(':')[1].strip()

    def read_rec_csv(self):
        '''Reads the actual data in the receptor file to a pandas dataframe for later reference'''
       
        rec_df = pd.read_csv(self.full_filepath,header = 6)
        rec_df['run_times'] = pd.to_datetime(rec_df['run_times'])
        return rec_df   

    def split_recdf_bytime(self):
        '''Splits the receptor dataframe into a list of dataframes, with each having the same run_time (the vertical levels for that run_time)
        
        Returns:
        split_dfs (list): list of dataframes, where each is a dataframe of a single run time representing the vertical levels
        '''
       
        split_dfs = [] #initialize the timegrouped list
        for name, group in self.rec_df.groupby('run_times'): #groupby runtime
            sub_df = group.copy() #copy to avoid overwriting
            split_dfs.append(sub_df) #append the df to the list

        return split_dfs    

class met_loader_ggg:
    '''Class to handle loading meteorological data that has been formatted for use in GGG/EGI.
    Generally, data should be split into daily files of the form YYYYMMDD_em27id.siteid.txt, where em27id is the two character
    id like "UA" or "HA", and siteid is the mesowest site id like "WBB". 

    These files should contain the following columns:
    'UTCDate' : Date in UTC of form yy/mm/dd
    'UTCTime' : Time in UTC of form HH:MM:SS
    'Pout' : outside pressure, in hPa
    'Tout' : outside temperature, in deg C
    'RH' : relative humidity, in %
    'WSPD' : wind speed, in m/s
    'WDIR' : wind direction, in degrees clockwise from north
    'wind_na' : boolean indicating whether the WSPD was na in the raw data (changed to 0.0 for use in GGG, should be changed back)


    '''

    def __init__(self,daily_met_path,column_mapper = None):
        '''
        Args:
        daily_met_path (str) : path to where the daily txt met files are stored
        column_mapper (dict) : a dictionary to change names of the columns, default None which gives the default mapper below
        '''

        self.daily_met_path = daily_met_path
        if column_mapper == None: #Map to new names of columns, can specify if needed or use the default below
            self.column_mapper = {'Pout':'pres','Tout':'temp','RH':'rh','WSPD':'ws','WDIR':'wd'} #default mapper for ggg formatted data

    def load_data_inrange(self,dt1,dt2):
        '''Loads all of the met data within a certin datetime range
        
        Args:
        dt1 (datetime.datetime) : a timezone aware datetime to start the data period
        dt2 (datetime.datetime) : a timezone aware datetime to end the data period
        
        Returns:
        full_dataframe (pandas.DataFrame) : a dataframe of all of the met data in the range, with a datetime index wind columns corrected
        '''
        if not dt1.tzinfo == pytz.utc: #the ggg data is stored in UTC, so convert to utc if the input dts are not in that timezone
            dt1 = dt1.astimezone(pytz.utc)
            dt2 = dt2.astimezone(pytz.utc)

        files_in_range = self.get_files_inrange(dt1,dt2) #get the files that are in the range 
        full_dataframe = pd.DataFrame() #initialize the full dataframe
        for fname in files_in_range: #loop through the files in the range
            df = self.load_format_single_file(fname) #load and format the individual file
            full_dataframe = pd.concat([full_dataframe,df]) #concatenate it into the big dataframe
        full_dataframe = full_dataframe.loc[(full_dataframe.index>=dt1) & (full_dataframe.index<=dt2)] #snip the dataframe to the range
        return full_dataframe

    def load_format_single_file(self,fname):
        '''Loads and formats a single met file given the filename
        
        Args: 
        fname (str) : name of the file in the self.daily_met_path folder to load
        
        Returns:
        df (pandas.DataFrame) : loaded and formated dataframe including datetime index and wind correction
        '''

        df = self.load_single_file(fname) #load the file
        df = self.add_dt_index(df) #add the dt as an index
        df = self.change_col_names(df) #change the column names
        df = self.wind_handler(df) #handle the wind values (deal with na and add u/v columns)
        return df

    def load_single_file(self,fname):
        '''Reads in a single file to a dataframe
        
        Args: 
        fname (str) : name of the file in the self.daily_met_path folder to load
        
        Returns:
        df (pandas.DataFrame) : raw loaded dataframe
        '''

        fullpath = os.path.join(self.daily_met_path,fname) #get the full path
        df = pd.read_csv(fullpath) #load the file
        return df
    
    def add_dt_index(self,df):
        '''Adds an index corresponding to the datetime based on the ggg file structure
        
        Args:
        df (pandas.DataFrame) : a dataframe loaded from a ggg style txt met file
        
        Returns:
        df (pandas.DataFrame) : the same dataframe, with a datetime index that is timezone aware (ggg style files should always be UTC)
        '''

        df.index = pd.to_datetime(df['UTCDate']+' '+df['UTCTime'],format='%y/%m/%d %H:%M:%S').dt.tz_localize('UTC') #parse the datetime
        return df
    
    def change_col_names(self,df):
        '''Changes the column names from a loaded dataframe to those in self.column_mapper 
        
        Args:
        df (pandas.DataFrame) : a dataframe loaded from a ggg style txt met file
        
        Returns:
        df (pandas.DataFrame) : the same dataframe, with the column names changed
        '''

        return df.rename(columns = self.column_mapper)

    def wind_handler(self,df):
        '''This handles the wind columns which are often manipulated to allow for running in EGI.
        
        Read more in mesowest_met_handler.py. Basically, we can't have any NaNs or blanks in the wind columns to run EGI, so we replace them 
        with 0.0. However, this does not mean they are actually 0, so we have added a "wind_na" column indicating if the wind speed values
        are actually 0 or if they were na. Wind direction values will always be na if windspeed is either 0 or na. 
        
        Args:
        df (pandas.DataFrame) : a dataframe loaded from a ggg style txt met file
        
        Returns:
        df (pandas.DataFrame) : the same dataframe with na values put in the right spots, and u and v wind vector columns added
        '''
        df.loc[df['ws'] == 0, 'ws'] = np.nan #can't have a wind direction if the wind speed is 0, so set it to nan
        if 'wind_na' in df.columns: #if there isn't a wind_na column, just return the dataframe
            df.loc[df['wind_na'] == True, 'ws'] = np.nan #if the windspeed was na (wind_na is true), set it back to na instead of 0 
        df[['u','v']] = df.apply(lambda row: wdws_to_uv(row['ws'],row['wd']),axis = 1,result_type='expand') #add wind columns for u and v to do averaging if needed
        return df
        
    def get_files_inrange(self,dt1,dt2):
        '''This gets the files that contain data in the range between dt1 and dt2
        
        Args:
        dt1 (datetime.datetime) : a timezone aware datetime to start the data period
        dt2 (datetime.datetime) : a timezone aware datetime to end the data period
        
        Returns:
        files_in_range (list) : a list of filenames only, in the self.daily_met_path, that fall in the dt range
        '''
        daystrings_in_range = [] #initialize the day strings in the range
        delta_days = dt2.date()-dt1.date() #get the number of days delta between the end and the start
        for i in range(delta_days.days +1): #loop through that number of days 
            day = dt1.date() + datetime.timedelta(days=i) #get the day by incrementing by i (how many days past the start)
            daystrings_in_range.append(day.strftime('%Y%m%d')) #append a string of the date (YYYYmmdd) to match with filenames
        files_in_range = [] #initilize the filenames that will be in the range
        for file in self.get_sorted_fnames(): #loop through the sorted oof files in the data folder
            for daystring_in_range in daystrings_in_range: # loop through the daystrings that are in the range
                if daystring_in_range in file: #if the daystring is in the filename, 
                    files_in_range.append(file) #append it. Otherwise keep going
        return files_in_range

    def get_sorted_fnames(self):
        '''Sorts the filenames within the daily met path
        
        Returns:
        (list) : a sorted list of all of the elements within the daily_met_path
        '''
        
        return sorted(os.listdir(self.daily_met_path))
    
class met_loader_trisonica:
    '''Class to handle loading meteorological data that has been collected by a Trisonica anemometer
    Generally, data are recorded as daily files of the form YYYYMMDD_anem.txt. 

    The form of these files is a bit weird. There are often blank lines between lines of data, and the data lines look something like this:
    ET= 1690299686.988468 DT= 2023-07-25 15:41:26.988468 S  02.61 D  073 U -02.48 V -00.77 W -00.30 T  20.56 H  68.93 DP  14.66 P  849.52 \
        AD  0.9979916 PI -000.1 RO -001.5 MD  011 TD  011
    
    '''

    def __init__(self,daily_met_path,resample_interval,column_mapper=None):
        '''
        Args:
        daily_met_path (str) : path to where the daily txt met files are stored
        '''

        self.daily_met_path = daily_met_path
        self.resample_interval = resample_interval
        self.headers_list = ['ET','Date','Time','S','D','U','V','W','T','H','DP','P','AD','PI','RO','MD','TD']
        if column_mapper == None: #Map to new names of columns, can specify if needed or use the default below
            self.column_mapper = {'U':'u','V':'v','W':'w','T':'temp','P':'pres','H':'rh','WDIR':'wd'} #default mapper for ggg formatted data


    def load_data_inrange(self,dt1,dt2):
        '''Loads all of the met data within a certin datetime range
        
        Args:
        dt1 (datetime.datetime) : a timezone aware datetime to start the data period
        dt2 (datetime.datetime) : a timezone aware datetime to end the data period
        
        Returns:
        full_dataframe (pandas.DataFrame) : a dataframe of all of the met data in the range
        '''

        files_in_range = self.get_files_inrange(dt1,dt2) #get the files that are in the range 
        full_dataframe = pd.DataFrame() #initialize the full dataframe
        for fname in files_in_range: #loop through the files in the range
            df = self.load_format_single_file(fname) #load and format the individual file
            full_dataframe = pd.concat([full_dataframe,df]) #concatenate it into the big dataframe
        full_dataframe = full_dataframe.loc[(full_dataframe.index>=dt1) & (full_dataframe.index<=dt2)] #snip the dataframe to the range
        full_dataframe['ws'],full_dataframe['wd'] = np.vectorize(uv_to_wdws)(full_dataframe['u'],full_dataframe['v'])
        return full_dataframe

    def load_format_single_file(self,fname):
        '''Loads and formats a single met file given the filename
        
        Args: 
        fname (str) : name of the file in the self.daily_met_path folder to load
        
        Returns:
        df (pandas.DataFrame) : loaded and formated dataframe including datetime index 
        '''

        fullpath = os.path.join(self.daily_met_path,fname) #get the full path
        with open(fullpath,'r',errors='ignore') as f: #we need to do some more sophisticated loading
            rows_list = [] #initialize a list to store the rows of data
            for i,line in enumerate(f): #loop through each line in the file
                newline = line.strip() #strip the newline character
                if len(newline) < 5: #if there are less than 5 characters, it's a bad line, so skip it
                    continue
                newline = newline.replace('=','') #replace equal signs with nothing
                for let in string.ascii_letters.replace('n','').replace('a',''): #replace any ascci characters with nothing
                    newline = newline.replace(let,'')
                newline = newline.replace(',',' ') #replace commas with a space
                if newline[0] == ' ': #if the line starts with a space, remove it
                    newline = newline[1:]
                newline = re.sub(r"\s+",",",newline) #substitute whitespace with a comma
                line_to_append = newline.split(',') # split the line by comma, should be all the good data
                if len(line_to_append) == len(self.headers_list): #check to make sure the number of data elements from the split lines matches the headers 
                    rows_list.append(line_to_append) #if so, append it to the rows list
            df = pd.DataFrame(rows_list) #create a dataframe from the rows
            df.columns = self.headers_list #set the columns to be the headers from the headers list
            for col in df.columns: #make the data numeric for all columns
                df[col] = pd.to_numeric(df[col],errors='coerce')
            df = df.dropna(axis = 1,how = 'all') #drop na where all
            df['DT'] = pd.to_datetime(df['ET'],unit='s') #set the datetime using the epoch time
            df = df.set_index('DT') #make the datetime the index
            df.index = df.index.tz_localize('UTC') #add timezone to index, should be UTC
            df = df.drop(['S','D'],axis = 1) #drop speed and direction since we have U and V and don't want to mess up averaging 
        if self.resample_interval is not None:
            df = df.resample(self.resample_interval).mean(numeric_only=True) #resample
        df = df.rename(columns = self.column_mapper) #rename the columns
        return df
    
    def get_files_inrange(self,dt1,dt2):
        '''This gets the files that contain data in the range between dt1 and dt2
        
        Args:
        dt1 (datetime.datetime) : a timezone aware datetime to start the data period
        dt2 (datetime.datetime) : a timezone aware datetime to end the data period
        
        Returns:
        files_in_range (list) : a list of filenames only, in the self.daily_met_path, that fall in the dt range
        '''
        daystrings_in_range = [] #initialize the day strings in the range
        delta_days = dt2.date()-dt1.date() #get the number of days delta between the end and the start
        for i in range(delta_days.days +1): #loop through that number of days 
            day = dt1.date() + datetime.timedelta(days=i) #get the day by incrementing by i (how many days past the start)
            daystrings_in_range.append(day.strftime('%Y%m%d')) #append a string of the date (YYYYmmdd) to match with filenames
        files_in_range = [] #initilize the filenames that will be in the range
        for file in self.get_sorted_fnames(): #loop through the sorted oof files in the data folder
            for daystring_in_range in daystrings_in_range: # loop through the daystrings that are in the range
                if daystring_in_range in file: #if the daystring is in the filename, 
                    files_in_range.append(file) #append it. Otherwise keep going
        return files_in_range

    def get_sorted_fnames(self):
        '''Sorts the filenames within the daily met path
        
        Returns:
        (list) : a sorted list of all of the elements within the daily_met_path
        '''
        
        return sorted(os.listdir(self.daily_met_path))

class HRRR_ARL_Getter:
    """A class to handle getting the hrrr arl met data for running STILT 
        
    """

    def __init__(self,configs,dt1,dt2):
        self.configs = configs
        self.dt1 = dt1
        self.dt2 = dt2
        self.save_dir = self.configs.folder_paths['met_folder']
        self.ftp = None

    def get_hrrr_met(self):
        """Gets the hrrr met files needed for the STILT run"""
        print('Retrieving HRRR data from NOAA ARL')
        self.setup_ftp()
        dtrange_met = self.get_hrrr_dtrange()
        hrrr_filelist = self.create_hrrr_filelist(dtrange_met)
        tot_size = self.check_all_sizes(hrrr_filelist)
        print(f'Downloading {len(hrrr_filelist)} files from {hrrr_filelist[0]} to {hrrr_filelist[-1]}')
        print(f'Total size of files to download: {tot_size/1e9:.2f} GB\n***This may take a while***')
        self.download_all_files(hrrr_filelist)
        self.remove_ftp()

    def setup_ftp(self):
        """Setup the ftp connection and save it to self"""
        ftp = FTP('ftp.arl.noaa.gov')
        ftp.login('anonymous',self.configs.ftp_email)
        ftp.cwd('archives/hrrr')
        self.ftp = ftp

    def get_hrrr_dtrange(self):
        """Gets the datetime range needed for the hrrr met files based on the input and configs"""
        n_hours = self.configs.run_stilt_configs['n_hours'] 
        tdelt_before = datetime.timedelta(hours=n_hours)
        
        # Adjust dt1 and dt2 to the nearest 6-hour interval
        dt1_adjusted = self.dt1 + tdelt_before
        dt1_adjusted = dt1_adjusted.replace(hour=(dt1_adjusted.hour // 6) * 6, minute=0, second=0, microsecond=0)
        
        dt2_adjusted = self.dt2
        dt2_adjusted = dt2_adjusted.replace(hour=((dt2_adjusted.hour // 6)) * 6 % 24, minute=0, second=0, microsecond=0)

        # Generate the datetime range with a frequency of 6 hours
        dtrange_met = pd.date_range(start=dt1_adjusted, end=dt2_adjusted, freq='6h')
        return dtrange_met
    
    def create_hrrr_filelist(self,dtrange_met):
        """Creates a list of hrrr files to download based on the datetime range"""
        hrrr_filelist = []
        for dt in dtrange_met:
            start_hour = f'{datetime.datetime.strftime(dt,"%H")}'
            end_hour = f'{datetime.datetime.strftime(dt + datetime.timedelta(hours=5),"%H")}'
            hrrr_file = f'{datetime.datetime.strftime(dt,"%Y%m%d")}_{start_hour}-{end_hour}_hrrr'
            if os.path.exists(os.path.join(self.save_dir,hrrr_file)):
                print(f'{hrrr_file} already exists in {self.save_dir}, skipping')
                continue
            hrrr_filelist.append(hrrr_file)
        return hrrr_filelist
    
    def check_single_fsize(self,fname):
        """Checks the size of a single file"""
        if not hasattr(self, 'ftp'):
            raise ValueError('FTP connection not established')
        self.ftp.sendcmd('TYPE i')
        fsize = self.ftp.size(fname)
        return fsize

    def check_all_sizes(self,hrrr_filelist):
        """Checks the size of all files in the filelist"""
        tot_size = 0
        for fname in hrrr_filelist:
            fsize = self.check_single_fsize(fname)
            tot_size += fsize
        return tot_size

    def download_hrrr_file(self,fname):
        """Downloads a single file"""
        print('Downloading ',fname)
        if not hasattr(self, 'ftp'):
            raise ValueError('FTP connection not established')
        with open(f'{self.save_dir}/{fname}', 'wb') as f:
            self.ftp.retrbinary(f'RETR {fname}', f.write)

    def download_all_files(self,hrrr_filelist):
        """Downloads all files in the filelist"""
        for fname in hrrr_filelist:
            self.download_hrrr_file(fname)

    def remove_ftp(self):
        """Closes the ftp connection and sets it to None"""
        self.ftp.quit()
        self.ftp = None

def main():
    #output_dir = '/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/STILT/stilt/out'
    #get_stilt_ncfiles(output_dir)
    #copy_em27_oofs_to_singlefolder('/uufs/chpc.utah.edu/common/home/lin-group15/agm/em27/ha/results','/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Data/EM27_oof/fall_2023')


    #the full dataset as of now is between the below dates
    import time
    import sys
    t1 = time.time()

    dt1_str = '2023-11-20 00:00:00'
    dt2_str = '2023-12-01 00:00:00' 
    timezone = 'US/Mountain'
    data_folder = '/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Data/EM27_oof/SLC_EM27_ha_2022_2023_oof_v2_nasrin_correct'
    cols_to_load = ['xch4(ppm)','solzen(deg)']
    dt1 = dtstr_to_dttz(dt1_str,timezone)
    dt2 = dtstr_to_dttz(dt2_str,timezone)
    my_oof_manager = oof_manager(data_folder,timezone)
    df = my_oof_manager.load_oof_df_inrange(dt1,dt2,cols_to_load=cols_to_load)

    t2 = time.time()
    print(t2-t1)
    print(df.describe())
    print(list(df.columns))

if __name__ == "__main__":
   main()