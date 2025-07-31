#Custom receptor load from receptor path and filenames, to be written in new_run_stilt by stilt_setup.py
receptors = data.frame()
for (rec_filename in rec_filenames){
  rec <- read.csv(file.path(rec_path,rec_filename), skip=7)
  rec$run_times <- ymd_hms(rec$run_times)
  rec$z_is_agl <- as.logical(rec$z_is_agl)
  rec2 <- rec[rec$z_is_agl==TRUE,]
  receptors = rbind(receptors,rec2)
}