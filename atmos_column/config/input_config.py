column_type = 'ground'
interval = '1H'
data_filter = None
start_dt_str = '2022-06-16 18:00:00' #start datetime
end_dt_str = '2022-06-18 15:00:00' #end datetime
timezone='UTC' #timezone of collected data. for now, this should be UTC as the EM27 stores data in UTC
inst_lat = 40.766
inst_lon = -111.847
inst_zasl = 1492 #instrument elevation in meters above sea level
# folder_paths = {'column_data_folder':'/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Data/EM27_oof/SLC_EM27_ha_2022_oof_v2',
#                 'hrrr_data_folder':'/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Data/hrrr',
#                 'output_folder':'/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Atmos_Column/output',
#                 'stilt_folder':'/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/STILT'}
folder_paths = {'column_data_folder':'/Users/agmeyer4/Google Drive/My Drive/Documents/LAIR/Data/SLC_EM27_ha_2022_oof_v2/',
                'hrrr_data_folder':'/Users/agmeyer4/LAIR_1/Data/hrrr',
                'output_folder':'/Users/agmeyer4/LAIR_1/Atmos_Column/output',
                'stilt_wd':'/Users/agmeyer4/LAIR_1/STILT'}
hrrr_subset_datestr='2022-07-01 00:00'
z_ail_list = [0,25,50,75,100,150,200,300,400,600,1000,1500,2000,2500]