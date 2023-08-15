import pandas as pd
import numpy as np
import os

def load_zeno(fullpath_name):
    with open(fullpath_name,'r') as f:
        lines=f.readlines()
    header = ['UTCDate','UTCTime','WSPD','WDIR','SigTheta','Gust','Tout','RH','Pout','Sflux','Precip','LeafWet','Bit','Battery']
    builddict = {key: [] for key in header}
    for line in lines:
        try:
            splitline = line.split(',')
            linedict = {key: np.nan for key in header}
            linedict['UTCDate']=splitline[1]
            linedict['UTCTime']=splitline[2]
            for i in range(6,len(splitline)-1):
                linedict[header[i-4]] = splitline[i]
        except Exception as e:
            print(line)
            print(e)
            continue
        for key in builddict.keys():
            builddict[key].append(linedict[key])

    df = pd.DataFrame(builddict)
    for col in header[2:]:
        df[col] = df[col].astype(float)
    df = df.dropna()
    return df

def fname_changer(fname):
    split = fname.split('-')
    yr = split[1]
    mo = split[2]
    da = split[3].split('.')[0]
    newfname = f'{yr}{mo}{da}_lanlZenoPoff.txt'
    return newfname

def apply_pressure_offset(df,poff):
    df['Pout'] = df.apply(lambda row: row['Pout'] + poff,axis = 1)
    return df

if __name__ == "__main__":
    in_folder = input("Enter Path to Input Folder: ")
    out_folder = input("Enter Path to Output Folder: ")
    poff = input("Enter Pressure Offset Value (float), or press enter for standard (-0.2): ")
    if not os.path.isdir(in_folder):
        raise Exception('Input folder path not found')
    if not os.path.isdir(out_folder):
        os.mkdir(out_folder)
    try:
        if poff == '':
            poff = -0.2
        else:
            poff = float(poff)
    except:
        print('input pressure offset either not a valid float or blank line.')
        print('setting poff to -0.2')
        poff = -0.2

    fnames = os.listdir(in_folder)
    for fname in fnames:
        print(f'Processing {fname}')
        fullpath_name = os.path.join(in_folder,fname)
        loaded_df = load_zeno(fullpath_name)
        poff_df = apply_pressure_offset(loaded_df,poff)
        out_fname = fname_changer(fname)
        out_fullpath_name = os.path.join(out_folder,out_fname)
        loaded_df.to_csv(out_fullpath_name,na_rep='0',index=False)