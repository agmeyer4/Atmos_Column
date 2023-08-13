import pandas as pd
import datetime 
import numpy as np
import os 

def load_vaisala_tph(fullpath_name):
    with open(fullpath_name,'r') as f:
        lines = f.readlines()

    ets = []
    dts = []
    datestrings = []
    timestrings = []
    ps = []
    ts = []
    rhs = []

    for line in lines:
        line = line.strip()
        if len(line)==0:
            continue
        try:
            et = float(line.split()[1])
            dt = datetime.datetime.utcfromtimestamp(et)
            date_string = dt.strftime('%y/%m/%d')
            time_string = dt.strftime('%H:%M:%S')
            p = float(line.split()[6])
            t = float(line.split()[9])
            rh = float(line.split()[12])

            ets.append(et)
            dts.append(dt)
            datestrings.append(date_string)
            timestrings.append(time_string)
            ps.append(p)
            ts.append(t)
            rhs.append(rh)
        except Exception as e:
            #print(line)
            #print(e)
            continue

    df = pd.DataFrame({
        'ET':ets,
        'DT':dts,
        'UTCDate':datestrings,
        'UTCTime':timestrings,
        'Pout':ps,
        'Tout':ts,
        'RH':rhs
    })

    nacol = ['WSPD','WDIR','SigTheta','Gust','Sflux','Precip','LeafWet','Bit','Battery']
    for col in nacol:
        df[col]=np.nan

    df = df[['UTCDate','UTCTime','WSPD','WDIR','SigTheta','Gust','Tout','RH','Pout','Sflux','Precip','LeafWet','Bit','Battery']]
    return df

if __name__ == "__main__":
    in_folder = input("Enter Path to Input Folder: ")
    out_folder = input("Enter Path to Output Folder: ")
    if not os.path.isdir(in_folder):
        raise Exception('Input folder path not found')
    if not os.path.isdir(out_folder):
        os.mkdir(out_folder)

    fnames = os.listdir(in_folder)
    for fname in fnames:
        print(f'Processing {fname}')
        fullpath_name = os.path.join(in_folder,fname)
        loaded_df = load_vaisala_tph(fullpath_name)
        out_fname = f'{fname.split(".")[0]}_fix.txt'
        out_fullpath_name = os.path.join(out_folder,out_fname)
        loaded_df.to_csv(out_fullpath_name,na_rep='0',index=False)
