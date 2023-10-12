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
            if not pd.col_is_equal(oof_df[col]):
                raise Exception('{col} is not the same for the entire oof_df. This is an edge case.')
        #If we make it through the above, we can pull the values from the dataframe at the 0th index because they are all the same
        inst_lat = oof_df.iloc[0]['inst_lat']
        inst_lon = oof_df.iloc[0]['inst_lon']
        inst_zasl = oof_df.iloc[0]['inst_zasl']
        return inst_lat,inst_lon,inst_zasl   
    
def load_oco_df(oco_data_fullpath,quality_flag = 0):
    xr_ds = xr.open_dataset(oco_data_fullpath)
    oco_df = xr_ds[['xco2','time','latitude','longitude','xco2_quality_flag']].to_dataframe().reset_index(drop=True)
    oco_df['dt'] = oco_df['time'].dt.tz_localize('UTC')
    oco_df = oco_df.drop('time',axis =1)
    if quality_flag is not None:
        oco_df = oco_df.loc[oco_df['xco2_quality_flag']==quality_flag]
    return oco_df

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

def trim_oco_df_to_extent(oco_df,extent):
    trimmed_df = oco_df.copy()
    trimmed_df = trimmed_df.loc[(trimmed_df['longitude']>=extent['lon_low'])&
                                (trimmed_df['longitude']<=extent['lon_high'])&
                                (trimmed_df['latitude']>=extent['lat_low'])&
                                (trimmed_df['latitude']<=extent['lat_high'])]
    return trimmed_df

def add_oco_inradius_column(df,inst_loc,radius_m):
    return_df = df.copy()
    return_df['dist_from_inst'] = np.vectorize(haversine)(inst_loc['lat'],inst_loc['lon'],return_df['latitude'],return_df['longitude'])
    return_df['inradius'] = return_df['dist_from_inst']<=radius_m
    return return_df

def get_oco_details(oco_df):
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
    oof_df['in_oco_window'] = (oof_df.index>=oco_details['oco_window_start']-oof_surround_time)&(oof_df.index<=oco_details['oco_window_end']+oof_surround_time)
    return oof_df

def get_oof_details(oof_df):
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
    to_bin = lambda x: np.floor(x/step_deg)*step_deg
    oco_df['latbin'] = to_bin(oco_df['latitude'])
    oco_df['lonbin'] = to_bin(oco_df['longitude'])
    binned_xr = oco_df.groupby(['latbin','lonbin']).mean(numeric_only=True).to_xarray()
    return binned_xr

def get_plottext_from_details(oco_details,oof_details):
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

if __name__ == "__main__":
    oco_data_folder = '/Users/agmeyer4/LAIR_1/Data/OCO/OCO2/'
    oof_data_folder = '/Users/agmeyer4/LAIR_1/Data/EM27_oof/SLC_EM27_ha_2022_oof_v2_nasrin_correct/'
    map_extent={'lon_low':-112.4,
                'lon_high':-111.6,
                'lat_low':40.5,
                'lat_high':41.0}
    inst_loc = {'lat':40.768,'lon':-111.854}
    radius = 6000
    oof_surround_time = datetime.timedelta(minutes=30)

    oco_filename = 'oco2_LtCO2_221003_B11100Ar_230609093747s.nc4'
    oof_filename = 'ha20221003.vav.ada.aia.oof'

    oco_df = load_oco_df(os.path.join(oco_data_folder,oco_filename),quality_flag=0)
    trimmed_oco_df = trim_oco_df_to_extent(oco_df,map_extent)
    trimmed_oco_df = add_oco_inradius_column(trimmed_oco_df,inst_loc,radius)
    inradius_oco_df = trimmed_oco_df.loc[trimmed_oco_df['inradius']]
    inradius_oco_details = get_oco_details(inradius_oco_df)

    my_oof_manager = oof_manager(oof_data_folder,'UTC')
    oof_df = my_oof_manager.df_from_oof(oof_filename,fullformat = True, filter_flag_0=True)
    oof_df = add_oof_inwindow_column(oof_df,inradius_oco_details,oof_surround_time)
    inwindow_oof_df = oof_df.loc[oof_df['in_oco_window']]
    inwindow_oof_details = get_oof_details(inwindow_oof_df)

    step_deg = 0.02
    binned_oco_xr = bin_oco_soundings(trimmed_oco_df,step_deg)
    plot_text = get_plottext_from_details(inradius_oco_details,inwindow_oof_details)

    labsize = 12
    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(10,8))
    ax = plt.axes(projection = proj)
    ax.set_extent([map_extent['lon_low'],map_extent['lon_high'],map_extent['lat_low'],map_extent['lat_high']],crs=proj)
    request = cimgt.GoogleTiles(style='satellite')
    scale = 9.0 # prob have to adjust this
    ax.add_image(request,int(scale))

    map = binned_oco_xr['xco2'].plot.pcolormesh('lonbin','latbin',ax = ax,alpha=0.7,cmap='viridis',add_colorbar=False)
    ax.scatter(inst_loc['lon'],inst_loc['lat'],color = 'red',marker = 'X',s = 100)

    cp = Geodesic().circle(lon=inst_loc['lon'],lat=inst_loc['lat'],radius = radius)
    geom = sgeom.Polygon(cp)
    ax.add_geometries(geom,crs=proj,edgecolor = 'k',facecolor='none')

    at = AnchoredText(plot_text, loc='upper left', frameon=True, borderpad=0.5, prop=dict(size=10))
    ax.add_artist(at)

    axins = inset_axes(ax,width='40%',height='20%',loc='lower left')
    axins.scatter(oof_df.index,oof_df['xco2(ppm)'],color = 'grey',zorder=3,s=1)
    if inradius_oco_details is not None:
            window_base = (min(oof_df.loc[oof_df['in_oco_window']].index),min(oof_df['xco2(ppm)']))
            width = max(oof_df.loc[oof_df['in_oco_window']].index)-min(oof_df.loc[oof_df['in_oco_window']].index)
            height = max(oof_df['xco2(ppm)'])-min(oof_df['xco2(ppm)'])+0.2
            rect = mpatches.Rectangle((window_base),width,height,zorder = 10,alpha = 0.5)
            axins.add_patch(rect)
    axins.tick_params(labelsize = labsize)
    axins.set_ylabel('EM27 XCO2 (ppm)',size = labsize-3)
    #axins.set_ylim([415,425])
    axins.xaxis.set_major_formatter(mdates.DateFormatter('%H', tz = datetime.timezone.utc))
    axins.set_xlabel(oof_df.index[0].strftime('%Z %b %d, %Y'),size = labsize)
    plt.gcf().autofmt_xdate()
    plt.colorbar(map,fraction=0.03,label ='XCO2 (ppm)')
    plt.show()