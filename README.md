# Atmos_Column

The Atmos_Column package is a python module for working with atmospheric "total column" or open path type measurments. Such measurement instruments include ground based solar spectrometers, remote sounding satellites/aircraft, and open path measurments. The module includes a wrapper for setting up and running STILT in the context of atmospheric column measurements.  ([Lin et al., 2003](https://doi.org/10.1029/2002JD003161), [Fasoli et al., 2018](https://doi.org/10.5194/gmd-11-2813-2018)). Also available are a variety of methods for loading, comparing and visualizing data from EM27, TCCON, OCO2/3, TROPOMI, and inventory data. 

**The main branch should be stable, but there are some dangling features that may not work.** This current version allows users to do the following:

- Calculate receptor positions for total column measurments on solar slant columns such as EM27/SUN spectrometers. This includes identifying "height above ground level" by pulling DEM data.
- Create formatted receptor files compatible with running STILT backtrajectories, either for generic slant columns or clipping to EM27 data ranges by pulling from .oof files. 
- Set up and configure the STILT runs by modifying the base "run_stilt.r" method in the STILT setup. 
- Run STILT using SLURM job submission
- Load, analyze, and visualize useful datasets including:
    - EM27 timeseries data
    - Meteorological data including MesoWest
    - Receptor details for STILT runs
    - STILT output footprints
    - Satellites 
        - OCO2/3
        - TROPOMI
    - Emissions Inventories
        - EPA (Maasakers) CH4
        - EDGAR CH4, CO2, CO
        - NOAA CSL *in progress*
    - KML file creation for Google Earth
    - File creation for use in R's OpenAir package

Work in progress includes:

- Applying pressure weighting functions and averaging kernels to produce accurate integrated total column footprints (from instruments such as EM27) from discrete receptor releases. 
- Visualizing footprints in the context of EM27 collected data.
- Adding functionality for open path data. 


# Project Setup Instructions

1. Create a project folder to house this work. My setup is currently as follows. Create the project folder and clone this Atmos_Column git repo into the project folder. I also include a Data folder (such as EM27_oof, and suface DEM data), and a STILT folder (within which the STILT generated repo will go) to house items I want outside the git folder.

```
├── base_project_folder
│   ├── Atmos_Column (this git repo)
│   │   ├── atmos_column
│   │   ├── environment.yml
│   │   ├── output
│   │   ├── slurm
│   │   └── README.md
│   ├── Data
│   │   ├── DEM
│   │   └── EM27_oof
│   └── STILT
```

2. Create a conda environment from the yml file, then activate it. Ensure you are in the base git directory Atmos_Column. I much prefer using mamba to create it, conda can get stuck. (https://mamba.readthedocs.io/en/latest/)
```
> mamba env create -f environment.yml
```  
or 
```
> conda env create -f environment.yml
```
then
```
> conda activate atmos_column1
```

3. If you plan on running STILT through this python wrapper, ensure that your R environment is properly configured. More information can be found in the [STILT docs](https://uataq.github.io/stilt/#/). Your configuration will need to be able to successfully run 
```
> Rscript -e "uataq::stilt_init('myproject')"
```

# Creating receptors and configuring for STILT

1. Edit or create a new input_config.json file in atmos_column/configs. These settings will drive the runs. See atmos_column/configs/input_config_description.txt for more information. The code will automatically look for config files in the folder described. 

2. To do a "full run", cd into atmos_column, check that your input config file is correctly named in the full_run.py main() function, and run the code below. **Note: default behavior for full_run.py is to split the datetime range into individual days, and run STILT on each day. This makes it easier to manage, rerun, and reconfigure data, rather than having one STILT project run the whole datetime range.**
```
> python full_run.py
``` 

3. You can also run the subroutines (create_receptors.py, stilt_setup.py) individually. Much like full_run.py, edit the main() function within these to reflect the correct input config path. Then simply run with Python
```
> python subroutinename.py
```

# Visualization and Documentation

Currently, two jupyter notebooks in atmos_column/ipynbs allow users to visualize data and understand how the code works

## Viz_Dev.ipynb
 - Working document for visualization
 - Interactive plotly figures for mapping receptors and their attributes
 - Step by step description for how receptors are created, analyzed, and saved
 - KML file creation for visualizing with Google Earth Pro

## basic_figs.ipynb
 - Figure creator for basic figures such as EM27 and met data time series
 - Allows users to interactively view EM27 time series data, identify interesting days, annotate create and save plots, and more. 

# Contact and Acknowledgements
This work is being carried out under the direction of Dr. John C. Lin in the Land-Atmosphere Interactions Research (LAIR) group at the University of Utah, Atmospheric Sciences Department. 

Please contact me directly with any questions or comments at agmeyer4@gmail.com. 

Produced by Aaron G. Meyer, 2023
