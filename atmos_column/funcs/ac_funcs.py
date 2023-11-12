'''
Module: ac_funcs.py
Author: Aaron G. Meyer (agmeyer4@gmail.com)
Description: This module contains functions and classes for doing atmospheric column analysis as part of the 
atmos_column package. Included are functions for loading and transforming oof data files from the EM27, dealing with slant columns,
loading HRRR data for terrain information, and producing receptor files for running STILT
'''

#Import Necessary Modules
import pandas as pd
import numpy as np
import os
import datetime
import itertools
import shutil
import pytz
import pysolar.solar as solar
from geographiclib.geodesic import Geodesic
from herbie import Herbie
import xarray as xr

#Functions     
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
    df1 = df1.reset_index() #reset the index, especially necessary in the case of multiindexing
    df1 = df1.reset_index() #reset it again so we can get a simulation id from the numerical index
    df1 = df1.rename(columns={lati_colname:'lati',long_colname:'long',zagl_colname:'zagl',
                              run_times_colname:'run_times',rec_is_agl_colname:'z_is_agl',
                              'index':'sim_id','receptor_zasl':'zasl','z_ail':'zail'}) #rename the columns

    df1 = df1[['run_times','lati','long','zagl','z_is_agl','sim_id','zasl','zail']] #only get the columns we need
    #do some rounding so we don't have to write a bunch of digits
    df1['lati'] = df1['lati'].round(4)
    df1['long'] = df1['long'].round(4)
    df1['zagl'] = df1['zagl'].round(2)
    df1['run_times'] = df1['run_times'].round('S')

    #TODO This sucks, want just an id then refer back to the receptor file for details. 
    #df1['sim_id'] = df1.apply(lambda row: f"{row['run_times'].year}_{row['run_times'].month}_{row['run_times'].day}_{row['index']}",axis=1)
    #df1['sim_id'] = df1.apply(lambda row: f"{row['run_times'].year}{row['run_times'].month:02}{row['run_times'].day:02}{row['run_times'].hour:02}{row['run_times'].minute:02}{row['run_times'].second:02}_{round(row['lati'],4)}_{round(row['long'],4)}_{round(row['zagl'],2)}_{row['index']}",axis=1)
    #df1['sim_id'] = df1['index']

    #df1['run_times'] = df1['run_times'].dt.tz_localize(None)
    df1 = df1.dropna() #drop na values, usually where the sun is not up 
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
        print('Point is outside the bounds of the HRRR grid')
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

def create_dt_list(dt1,dt2,interval):
    '''Creates a list of datetime elements within the range subject to an input interval
    
    Args:
    dt1 (datetime.datetime) : start datetime
    dt2 (datetime.datetime) : end datetime
    interval (str) : interval string like "1H", "2T" etc
    
    Returns:
    dt_list (list) : list of datetimes at the input interval between dt1 and dt2 inclusive
    '''

    dt_index = pd.date_range(dt1,dt2,freq=interval)
    dt_list = list(dt_index)
    return dt_list

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

    def load_oof_df_inrange(self,dt1,dt2,filter_flag_0=False):
        '''Loads a dataframe from an oof file for datetimes between the input values
        
        Args:
        dt1_str (str) : string for the start time of the desired range of form "YYYY-mm-dd HH:MM:SS" 
        dt2_str (str) : string for the end time of the desired range of form "YYYY-mm-dd HH:MM:SS" 
        oof_filename (str) : name of the oof file to load
        filter_flag_0 (bool) : True will filter the dataframe to rows where the flag column is 0 (good data), false returns all the data

        Returns:
        df (pd.DataFrame) : pandas dataframe loaded from the oof files, formatted date, and column names       
        '''
        if type(dt1) == str:
            dt1 = self.tzdt_from_str(dt1)
            dt2 = self.tzdt_from_str(dt2)
        oof_files_inrange = self.get_oof_in_range(dt1,dt2)
        full_df = pd.DataFrame()
        for oof_filename in oof_files_inrange:
            df = self.df_from_oof(oof_filename) #load the oof file to a dataframe
            df = self.df_dt_formatter(df) #format the dataframe to the correct datetime and column name formats
            df = df.loc[(df.index>=dt1)&(df.index<=dt2)] #filter the dataframe between the input datetimes
            if filter_flag_0: #if we want to filter by flag
                df = df.loc[df['flag'] == 0] #then do it!
            full_df = pd.concat([full_df,df])
        return full_df

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

    def df_from_oof(self,filename,fullformat = False,filter_flag_0 = False):
        '''Load a dataframe from an oof file
        
        Args:
        filename (str) : name of the oof file (not the full path)
        fullformat (bool) : if you want to do the full format
        
        Returns:
        df (pd.DataFrame) : a pandas dataframe loaded from the em27 oof file with applicable columns added/renamed
        '''

        oof_full_filepath = os.path.join(self.oof_data_folder,filename) #get the full filepath using the class' folder path
        df = pd.read_csv(oof_full_filepath,header = self.read_oof_header_line(oof_full_filepath),delim_whitespace=True,skip_blank_lines=False) #read it as a csv, parse the header
        df['inst_zasl'] = df['zobs(km)']*1000 #add the instrument z elevation in meters above sea level (instead of km)
        df['inst_lat'] = df['lat(deg)'] #rename the inst lat column
        df['inst_lon'] = df['long(deg)'] #rename the inst lon column 
        if fullformat:
            df = self.df_dt_formatter(df)
        if filter_flag_0:
            df = df.loc[df['flag']==0]
        return df

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

    def run_slant_at_intervals(self,dt1,dt2,my_dem_handler,interval='1H'):
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
            print('point is outside the DEMs range')
            return np.nan
        dem_df['dist'] = np.vectorize(haversine)(dem_df[self.dem_latname],dem_df[self.dem_lonname],pt_lat,pt_lon) #add a distance column for each subpoint using haversine
        idx = dem_df['dist'].idxmin() #find the minimum distance
        surface_height = dem_df.loc[idx][self.dem_dataname] #return the value requested
        return surface_height

def get_stilt_ncfiles(output_dir):
    by_id_fulldir = os.path.join(output_dir,'by-id')
    id_list = os.listdir(by_id_fulldir)
    #for id in id_list:
        # print(id)
        # try:
        #     print(f"{id}: {os.path.join(by_id_fulldir,id)/}")

def main():
    output_dir = '/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/STILT/stilt/out'
    get_stilt_ncfiles(output_dir)
    

if __name__ == "__main__":
   main()