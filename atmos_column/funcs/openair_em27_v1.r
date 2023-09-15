library(ggplot2)
library(grid)
library(openair)
library(latticeExtra)

df<-read.csv('~/LAIR/Data/flag0_interesting.csv')
df1<-head(df,10000)
#windRose(df)

polarPlot(df1,pollutant = 'xch4.ppm.',
                     statistic = 'cpf',percentile = 95,cols = 'viridis')
