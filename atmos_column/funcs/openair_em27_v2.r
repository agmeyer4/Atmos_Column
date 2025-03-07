library(ggplot2)
library(grid)
library(openair)
library(latticeExtra)


ch4_co2_ha<-read.csv('/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Projects/LAIR_mtg_2024/Data/202205-202409_5T_ch4_co2.csv')
polarPlot(ch4_co2_ha,pollutant = 'ch4_co2_r2',#ws='ws_roll',wd='wd_roll',
          statistic = 'percentile',percentile = 95,cols = 'viridis',par.settings=list(fontsize=list(text=25)))
polarPlot(ch4_co2_ha,pollutant = 'ch4_co2_slope',#ws='ws_roll',wd='wd_roll',
          statistic = 'percentile',percentile = 95,cols = 'viridis',par.settings=list(fontsize=list(text=25)))
polarPlot(ch4_co2_ha,pollutant = 'ch4_co2_slope',#ws='ws_roll',wd='wd_roll',
          statistic = 'mean',cols = 'viridis',par.settings=list(fontsize=list(text=25)))

co_co2_ha<-read.csv('/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Projects/LAIR_mtg_2024/Data/202205-202409_5T_co_co2.csv')
polarPlot(co_co2_ha,pollutant = 'co_co2_slope',#ws='ws_roll',wd='wd_roll',
          statistic = 'mean',cols = 'viridis',par.settings=list(fontsize=list(text=25)))
polarPlot(co_co2_ha,pollutant = 'co_co2_slope',#ws='ws_roll',wd='wd_roll',
          statistic = 'percentile',percentile = 95,cols = 'viridis',par.settings=list(fontsize=list(text=25)))
polarPlot(co_co2_ha,pollutant = 'co_co2_r2',#ws='ws_roll',wd='wd_roll',
          statistic = 'percentile',percentile = 95,cols = 'viridis',par.settings=list(fontsize=list(text=25)))



ch4_co2_ha<-read.csv('/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Projects/Ratio_paper_2024/Data/ch4_co2_5T.csv')
polarPlot(ch4_co2_ha,pollutant = 'ch4_co2_york_slope',#ws='ws_roll',wd='wd_roll',
          statistic = 'percentile',percentile = 95,cols = 'viridis',par.settings=list(fontsize=list(text=25)))
polarPlot(ch4_co2_ha,pollutant = 'ch4_co2_slope',#ws='ws_roll',wd='wd_roll',
          statistic = 'percentile',percentile = 95,cols = 'viridis',par.settings=list(fontsize=list(text=25)))
polarPlot(ch4_co2_ha,pollutant = 'ch4_co2_york_slope',#ws='ws_roll',wd='wd_roll',
          statistic = 'mean',cols = 'viridis',min.bin=1,par.settings=list(fontsize=list(text=25)))



