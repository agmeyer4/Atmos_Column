#Define the paths to important folders. Use full paths: doesn't like the "~" notation for $HOME
column_type = 'em27'

dt1_str = '2022-06-16 18:00:00' #start datetime
dt2_str = '2022-06-16 18:20:00' #end datetime
timezone='UTC' #timezone of collected data. for now, this should be UTC as the EM27 stores data in UTC

folder_paths = {'column_data_folder':'/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Data/EM27_oof/SLC_EM27_ha_2022_oof_v2',
                'hrrr_data_folder':'/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Data/hrrr',
                'output_folder':'/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Atmos_Column/output',
                'stilt_wd':'/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/STILT'}

# folder_paths = {'column_data_folder':'/Users/agmeyer4/Google Drive/My Drive/Documents/LAIR/Data/SLC_EM27_ha_2022_oof_v2/',
#                 'hrrr_data_folder':'/Users/agmeyer4/LAIR_1/Data/hrrr',
#                 'output_folder':'/Users/agmeyer4/LAIR_1/Atmos_Column/output',
#                 'stilt_wd':'/Users/agmeyer4/LAIR_1/STILT'}

hrrr_subset_datestr='2022-07-01 00:00'

z_ail_list = [0,25,50,75,100,150,200,300,400,600,1000,1500,2000,2500]