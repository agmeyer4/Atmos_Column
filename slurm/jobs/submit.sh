#!/bin/bash
#SBATCH --nodes=1
#SBATCH --account=carbon-kp
#SBATCH --partition=carbon-kp
#SBATCH -o /uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Atmos_Column/slurm/logs/%A.out
Rscript /uufs/chpc.utah.edu/common/home/lin-group15/agm/STILT_runs/test/20230711_stilt/r/ac_run_stilt.r
Rscript /uufs/chpc.utah.edu/common/home/lin-group15/agm/STILT_runs/test/20230712_stilt/r/ac_run_stilt.r
