'''
Script: mesowest_met_handler.py
Author: Aaron G. Meyer
Email: agmeyer4@gmail.com

This module is for formatting mesowest met data into a format that is ingestable by GGG by splitting a monthly mesowest
csv file into daily met files of the correct form and format. It does not include any "data grabbing" from the mesowest 
site -- this must be done manually for now. To use this module, follow the following steps:

1. Login to mymesowest (https://mesowest.utah.edu/cgi-bin/droman/my_mesowest.cgi)
2. Go to the main site (https://mesowest.utah.edu/). At left, under "station search", select site id from the 
   dropdown. In the seach box, enter the site id you want (for U of U, search 'wbb'). 
3. Once on the station page, click "Download Data" option on the left 
4. Select "Metric" under "Units in" dropdown. 
5. Select "GMT" under download by date dropdown instead of local (this will propogate to the mothly downloads 
   in step 6. ***This is critical to get UTC time in the files***
6. Select the "Download by Year & Month" option, and choose the year and month you'd like to download. 
7. Select "All Variables" for the "Available Variables" option. 
8. Click "Retrieve Data" at the bottom. This will download a file called WBB.csv or similar for your station
9. I like to rename this file to WBB.YYYYMM.csv, as otherwise they are not differentiated between different month
   downloads. 
10. Put the WBB.YYYYMM.csv file somewhere you know. 
11. Navigate to the main function of this module, and alter the variables to match your system:
    input_csv_fullpath = 'path/to/your/monthlydata/WBB.202311.csv' --name of the file you wish to split (what was downloaded above)
    output_folder = 'path/to/your/output/folder/daily_csvs' -- path to a folder where the daily split files will be written (needs to exist)
12. Run <python mesowest_met_handler.py> 
13. There now should be daily files in the output folder that have form readable by GGG. Point to these files in GGG
    or move them to the correct folder where GGG will find them. 
'''

import os
import pandas as pd

def split_and_write_daily(input_csv_fullpath,header_change,output_folder,instrument_tag=None):
    '''This is the main script to check a monthly mesowest data file, split it into daily files, format for use in GGG
    and write to separate day files (YYYYMMDD_WBB.txt). 
    
    Args: 
    input_csv_fullpath (str): full filepath of the monthly mesowest file to parse
    header_change (dict): the mapping from headers in the mesowest file to their appropriate headers for a GGG met file
    output_folder (str): path to a folder where the daily separated files will be stored
    instrument_tag (str): two letter tag to add to the filename indicating an EM27 instrument. Default None (no tag)
    '''

    is_utc = get_is_utc(input_csv_fullpath) #test to make sure the data is in UTC
    if not is_utc:  #if not, raise an excepthion
        raise Exception('Monthly data file is not in UTC time, check your download settings and try again')
    site_id = get_siteid(input_csv_fullpath)
    print(f'Load the full dataframe for {input_csv_fullpath}')
    full_df = load_transform_fullmonth(input_csv_fullpath,header_change) #load the entire month into a dataframe
    full_df = wind_na_replace(full_df) #replace the wind NA's for use in GGG. See function for more details. 
    daily_data = split_into_daydfs(full_df,site_id,instrument_tag = instrument_tag) #split into days
    for data in daily_data: #run through the days
        filename = data[0]
        df = data[1]
        print(f'Writing txt to {output_folder} for {filename}')
        write_to_txt(output_folder,filename,df) #and write them to txt files in the output folder

def get_siteid(input_csv_fullpath):
    '''Gets the site id (like WBB) from the header of the mesowest data file. 
    
    Args: 
    input_csv_fullpath (str) : full path to the file
    
    Returns:
    site_id (str) : the site id from the mesowest interface (like WBB)'''

    with open(input_csv_fullpath) as f: #open the file
        for i in range(0,10): #go through the first few lines, should be on 1?
            line = f.readline() #read the line
            if line.startswith('# STATION:'): #this is the indicator for the site id
                site_id = line.split(' ')[-1].strip() #split on space and get the last element, then strip the newline

    return site_id

def get_is_utc(input_csv_fullpath):
    '''Checks to make sure that the input mesowest file is in UTC time -- it should contain "UTC" in the data lines 
    instead of MDT or MST
    
    Args:
    input_csv_fullpath (str): full filepath of the monthly mesowest file
    
    Returns:
    (bool): True if it is in UTC, False if not
    '''

    with open(input_csv_fullpath) as f:
        for i in range(0,10):#the data startss on the 10th line, so read up to there instead of reading in the whole thing
            line = f.readline()
        if 'UTC' not in line: # The timezone (should be UTC) appears in each data line. If UTC is not in the line, it is in a different timezone
            return False
        else:
            return True

def load_transform_fullmonth(input_csv_fullpath,header_change):
    '''Load and transform the full month of data, including the pressure value change and datetime parsing
    
    Args:
    input_csv_fullpath (str): full filepath of the monthly mesowest file to parse
    header_change (dict): the mapping from headers in the mesowest file to their appropriate headers for a GGG met file

    Returns:
    full_df (pandas.DataFrame): a pandas dataframe of the form (headers, pressure values, etc) for writing to a txt for GGG
    '''

    full_df = pd.read_csv(input_csv_fullpath,header = 6,skiprows=lambda x : x == 7) #read in the csv, grab the header, and skip the row below the header (units row)
    full_df = full_df.rename(columns=header_change) #change the header labels to be consistent with GGG style
    full_df['Pout'] = full_df['Pout']/100 #convert from Pa to hPa
    full_df['dt'] = pd.to_datetime(full_df['dt']) #get the datetime from the dtstring column
    full_df = full_df.set_index('dt') #set the dt as the index for easy grouping later
    full_df['UTCDate'] = full_df.index.strftime('%y/%m/%d') #add a UTCDate column from the dt index
    full_df['UTCTime'] = full_df.index.strftime('%H:%M:%S') #add a UTCTime column from the dt index
    keep_cols = ['UTCDate','UTCTime'] + list(header_change.values()) #these are the columns we want to keep (utc date, time, and the new headers)
    keep_cols.remove('dt') #remove 'dt' from the keep columns as it is already the index, which we will drop when writing to txt
    full_df = full_df[keep_cols] #only keep the keep columns
    return full_df
        
def split_into_daydfs(full_df,site_id,instrument_tag):
    '''Splits a full month dataframe into individual days, and create the txt label based on date
    
    Args:
    full_df (pandas.DataFrame): a pandas dataframe of the form (headers, pressure values, etc) for writing to a txt for GGG
    site_id (str) : site id of the mesowest station, pulled from the header (like WBB)
    instrument_tag (str) : string indicating the EM27 instrument if desired. Added to the filename if not none. 

    Returns:
    daily_data (list): a list of lists. Each element of the list represents one day. The first subelement is the filename as 
                        YYYYMMDD_WBB.txt, and the second element is the dataframe for that day.
    '''

    daily_data = [] #intitialize the list
    for group in full_df.groupby(full_df.index.date): #group by date
        day_df = group[1] #the df is the 1 element of the list
        if instrument_tag is not None:
            day_label = f'{group[0].year:04d}{group[0].month:02d}{group[0].day:02d}_{instrument_tag}.{site_id}.txt' #this is the label of the file to be written
        else:
            day_label = f'{group[0].year:04d}{group[0].month:02d}{group[0].day:02d}.{site_id}.txt' #this is the label of the file to be written
        daily_data.append([day_label,day_df]) #append the label and df to the list 
    return daily_data

def wind_na_replace(df,ws_colname = 'WSPD',wd_colname = 'WDIR',replace_with = 0.0,add_na_indicator_col=True):
    '''Replaces na values in windspeed and wind dir columns. 
    
    EGI's metmatch fails when there are NA values in any of the met variables, including wind, which is not critical to the retrieval. So we replace
    NA's in wind speed and wind direction columns with 0.0 by default (user param). We can also add an indicator column for using the separated data, 
    which tell us if there was an NA in the wind speed column -- indicating bad data (true na_indicator). Since NA appears in the wind direction column when wind speed
    is 0.0, this is not indicative of bad data and the indicator would be false in this case. 
    
    Args:
    df (pandas.DataFrame) : dataframe with wind speed and direction columns
    ws_colname (str) : name of the windspeed column. Default "WSPD" to match EGI/GGG met data format
    wd_colname (str) : name of the wind direction column. Default "WDIR" to match EGI/GGG met data format
    replace_with (str, float, int) : what will replace "NA" in a wind column. Default 0.0 
    add_na_indicator_col (bool) : if true, will add a boolean column called "wind_na" that is true if wind speed is NA and false if not. 
    
    Returns:
    out_df (pandas.DataFrame) : dataframe with the NA values replaced and the new indicator column, if needed
    '''
    out_df = df.copy()
    if add_na_indicator_col: #if we want to add the indicator
        out_df['wind_na'] = out_df[ws_colname].isna() #add it for na values of winspeed
    out_df[wd_colname] = out_df[wd_colname].fillna(replace_with)   #replace 
    out_df[ws_colname] = out_df[ws_colname].fillna(replace_with)
    return out_df

def write_to_txt(folder_path,filename,df):
    '''Writes a dataframe to a file. Replaces na values in wind columns with 0*
    
    Args:
    folder_path (str): location where file should be written
    filename (str): what the file name should be
    df (str): the dataframe we wish to write
    '''

    fullpath = os.path.join(folder_path,filename) #get the full path of the file to be written, in the correct folder
    df.to_csv(fullpath,index=False) #write it to csv

if __name__ == "__main__":
    #This is the main function call. Edit the variable values appropriately. 
    #input_csv_fullpath = '/uufs/chpc.utah.edu/common/home/u0890904/Downloads/WBB_1.csv'
    output_folder = '/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Data/met/wbb/daily_txt_gggformat'
    header_change = {'Date_Time':'dt',
                    'pressure_set_1':'Pout',
                    'air_temp_set_1':'Tout',
                    'relative_humidity_set_1':'RH',
                    'wind_speed_set_1':'WSPD',
                    'wind_direction_set_1':'WDIR'}
    instrument_tag = 'HA'
    
    for fname in os.listdir('/uufs/chpc.utah.edu/common/home/u0890904/Downloads/'):
        if fname.startswith('WBB'):
            input_csv_fullpath = os.path.join('/uufs/chpc.utah.edu/common/home/u0890904/Downloads/',fname)
            split_and_write_daily(input_csv_fullpath,header_change,output_folder,instrument_tag=instrument_tag)
        else:
            continue

    #split_and_write_daily(input_csv_fullpath,header_change,output_folder,instrument_tag=instrument_tag)

