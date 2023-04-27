'''
Module: plotting.py
Author: Aaron G. Meyer (agmeyer4@gmail.com)
Description: Helpful plotting functions for visualizing atmospheric column data using plotly. 
'''

#Import Packages
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import simplekml

def add_slant_trace(fig,df,dt_str):
    '''Adds a slant trace to a plotly map
    
    Args:
    fig (go.Figure) : plotly figure
    df (pd.DataFrame) : pandas dataframe with "lat", "lon" and "z_ail" columns
    dt_str (string) : string representing the datetime of the measurement for labeling
    '''
    
    if 'receptor_shasl' in df.columns:
        mb = create_mapbox_withsh(df,dt_str)
    else:
        mb = create_mapbox_nosh(df,dt_str)
    fig.add_trace(
        mb
    )

def create_mapbox_withsh(df,dt_str):
    mb = go.Scattermapbox(	
            lat=df['receptor_lat'],
            lon=df['receptor_lon'],
            customdata=np.stack((df['z_ail'],df['receptor_zasl'],df['receptor_shasl'],df['receptor_zagl']), axis=-1),
            mode='markers+lines', #need markers and lines for hover to work 
            marker={
                'size':10,
            },
            hovertemplate = #sets up the hover data
                "<b>z above inst = %{customdata[0]:.0f}m </b><br>" + #bold and include the z information
                "<b>z above msl = %{customdata[1]:.0f}m </b><br>" + #bold and include the z information
                "<b>surface msl = %{customdata[2]:.0f}m </b><br>" + #bold and include the z information
                "<b>z above ground = %{customdata[3]:.0f}m </b><br>" + #bold and include the z information
                "longitude: %{lon:.3f}<br>" + #include the longitude
                "latitude: %{lat:.3f}<br>",  #include the lattitude
            name=dt_str, #name the whole trace based on the datetime string
        )
    return mb

def create_mapbox_nosh(df,dt_str):
    mb = go.Scattermapbox(	
            lat=df['receptor_lat'],
            lon=df['receptor_lon'],
            customdata=np.stack((df['z_ail'],df['receptor_zasl']), axis=-1),
            mode='markers+lines', #need markers and lines for hover to work 
            marker={
                'size':10,
            },
            hovertemplate = #sets up the hover data
                "<b>z above inst = %{customdata[0]:.0f}m </b><br>" + #bold and include the z information
                "<b>z above msl = %{customdata[1]:.0f}m </b><br>" + #bold and include the z information
                "longitude: %{lon:.3f}<br>" + #include the longitude
                "latitude: %{lat:.3f}<br>",  #include the lattitude
            name=dt_str, #name the whole trace based on the datetime string
        )
    return mb

def create_slant_plots(df,center_lat,center_lon,zoom=8,dt_str='',plot_interval=0):
    '''Creates a map with slant profiles using either a multiindex dataframe or a single dataframe with the correct column configuration
    
    Args:
    df (pd.DataFrame) : pandas dataframe in one of two forms \
                        a single index dataframe with "lat", "lon", and "z_asl" columns\
                        a multiindex dataframe with one index as the datetime, and one index as the z_ail. The main dataframes should have the columns listed above
    center_lat (float) : latitude of the center of the map
    center_lon (float) : lontitude of the center of the map
    zoom (float) : zoom level -- larger number corresponds to further away (default = 8)
    dt_str (string) : if a single indexed df is input, can supply the dt string which will be labeled in the hover and legend of the plot (default empty)
    
    Returns:
    a plotly graph objects figure
    '''
    
    fig = go.Figure() #initialize the fig
    oldET = 0
    #check if it's a multiindex dataframe
    if isinstance(df.index,pd.MultiIndex):  #if it is, need to loop through it
        for dt,newdf in df.groupby(level=0): #groupby the first index -- datetime
            dt_str = dt.strftime('%Y-%m-%d %H:%M:%S %Z') #grab the datetime string for labeling
            plotdf = newdf.droplevel(0).reset_index() #get the new dataframe at that datetime level and reset the index so z_asl is a column not an index
            if len(plotdf.dropna())==0: #if the sun is below the horizon, the dataframe at that time will be empty. We don't want to clutter the legend so just skip plotting those
                continue
            newET = dt.timestamp()
            if (newET-oldET)>plot_interval:
                add_slant_trace(fig,plotdf,dt_str)
                oldET=newET

    else: #if it's just a single indexed dataframe
        add_slant_trace(fig,df,dt_str) #just add that slant trance
 
    fig.update_layout( #update the layout
        mapbox_style="white-bg",
        mapbox_layers=[ #get sattelite data from usgs/canada
            {
                "below": 'traces',
                "sourcetype": "raster",
                "sourceattribution": "United States Geological Survey",
                "source": [
                    "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
                ]
            },
            {
                "sourcetype": "raster",
                "sourceattribution": "Government of Canada",
                "source": ["https://geo.weather.gc.ca/geomet/?"
                        "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&BBOX={bbox-epsg-3857}&CRS=EPSG:3857"
                        "&WIDTH=1000&HEIGHT=1000&LAYERS=RADAR_1KM_RDBR&TILED=true&FORMAT=image/png"],
            }
        ],
        mapbox=dict( #set the map parameters
            bearing=0,
            center=go.layout.mapbox.Center(
                lat=center_lat,
                lon=center_lon
            ),
            pitch=0,
            zoom=zoom
        ),
        height=400, #set the plot height
        showlegend=True, #show the legend
        hovermode='closest', #set the hovermode
        margin={"r":0,"t":0,"l":0,"b":0} #mess with the margins
        )
    return fig

def kml_color_list_generator(n,cmap_name='viridis'):
    cmap = plt.get_cmap(cmap_name)
    rgb_cmap = (cmap(np.linspace(0,1,n))*255).astype(int)
    kml_cmap = []
    for c in rgb_cmap:
        kml_cmap.append(simplekml.Color.rgb(c[0],c[1],c[2],c[3]))
    return kml_cmap