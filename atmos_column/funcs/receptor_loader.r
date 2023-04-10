rec_path = '/uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Atmos_Column/output/receptors/'
rec_filename = 'em27_20220616_20220616000000_20220616230000.csv'

rec <- read.csv(file.path(rec_path,rec_filename), skip=6)
rec$run_times <- as.POSIXct(rec$run_times,tz='UTC')
rec$z_is_agl <- as.logical(rec$z_is_agl)
rec2 <- rec[rec$z_is_agl==TRUE,]
