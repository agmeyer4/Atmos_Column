# Atmos_Column

The Atmos_Column package is a python wrapper for handling atmospheric "column" measurements like solar spectrometers, aircraft, and satellite remote sensing for use in atmospheric transport models like STILT ([Lin et al., 2003](https://doi.org/10.1029/2002JD003161), [Fasoli et al., 2018](https://doi.org/10.5194/gmd-11-2813-2018)).

**This is an in progress version. I am actively developing and features, bugs, configurations, etc. may change quickly.** This current version allows users to do the following:

- Calculate receptor positions for total column measurments on slant columns such as EM27/SUN spectrometers. This includes identifying "height above ground level" by pulling DEM data from HRRR files.
- Create formatted receptor files compatible with running STILT backtrajectories, either for generic slant columns or EM27 data by pulling from .oof files. 
- Set up and configure the STILT runs by modifying the base "run_stilt.r" method in the STILT setup. 
- Create basic figures for visualization. Current version has capabilities to interactively visualize EM27 time series data, interactive receptor mapping functions, and KML file creation for Google Earth implementation. 

Work in progress includes:

- Applying pressure weighting functions and averaging kernels to produce accurate integrated total column footprints (from instruments such as EM27) from discrete receptor releases. 
- Visualizing footprints in the context of EM27 collected data.
- Better setup for "full runs" and longer term analysis leveraging CHPC resources. 
- Addressing nuances related to receptor elevations above ground level (some receptors can be "below" ground level based on an above instrument input height)

# Project Setup Instructions

1. Create a project folder to house this work. My setup is currently as follows. Create the project folder and clone the Atmos_Column git repo into the project folder. I also include a Data folder (such as EM27_oof, and suface level HRRR data), and a STILT folder (within which the STILT generated repo will go) to house items I want outside the git folder.

```
├── project_folder
│   ├── Atmos_Column (this git repo)
│   │   ├── atmos_column
│   │   ├── environment.yml
│   │   ├── output
│   │   └── README.md
│   ├── Data
│   │   ├── EM27_oof
│   │   └── HRRR
│   └── STILT
```

2. Create a conda environment from the yml file, then activate it using:   
```
> conda env create -f environment.yml
```  
```
> conda activate atmos_column
```

3. If you plan on running STILT through this python wrapper, ensure that your R environment is properly configured. More information can be found in the [STILT docs](https://uataq.github.io/stilt/#/). Your configuration will need to be able to successfully run 
```
> Rscript -e "uataq::stilt_init('myproject')"
```

# Creating receptors and configuring for STILT

1. Edit or create a new input_config.json file in atmos_column/configs. These settings will drive the runs. See atmos_column/configs/input_config_description.txt for more information. 

2. To do a "full run" (up to the point I have developed), cd into atmos_column, check that your input config file is correctly named in the full_run.py main() function, and run:
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