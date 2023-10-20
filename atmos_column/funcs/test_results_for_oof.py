'''Basic script to check for oof files in a results folder, day by day'''

import os
results_folder = input('Base Results folder with cumulative/daily and date folders : ')
if not os.path.isdir(results_folder):
    raise NameError('No path of that name')
daily_folder = os.path.join(results_folder,'daily')
dates_list = os.listdir(daily_folder)
for date in sorted(dates_list):
    files = os.listdir(os.path.join(daily_folder,date))
    oof_exists = False
    for file in files:
        if file.endswith('.vav.ada.aia.oof'):
            oof_exists = True
            break
        else: 
            continue
    if oof_exists:
        print(f'OOF exists for {date}')
    else:
        print(f'***NO OOF FILE FOR {date}***')
