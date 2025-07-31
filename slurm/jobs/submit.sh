#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --partition=carbon-kp
#SBATCH --account=carbon-kp
#SBATCH --time=100:00:00
#SBATCH -o /uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Atmos_Column/slurm/logs/%A.out

SECONDS=0
echo "
-----------------------------
"
echo "Rscript /uufs/chpc.utah.edu/common/home/lin-group9/agm/STILT_runs/test/20230709/r/ac_run_stilt.r"
Rscript /uufs/chpc.utah.edu/common/home/lin-group9/agm/STILT_runs/test/20230709/r/ac_run_stilt.r
echo "Time since last = $SECONDS seconds"
SECONDS=0
echo "
-----------------------------
"
echo "Rscript /uufs/chpc.utah.edu/common/home/lin-group9/agm/STILT_runs/test/20230710/r/ac_run_stilt.r"
Rscript /uufs/chpc.utah.edu/common/home/lin-group9/agm/STILT_runs/test/20230710/r/ac_run_stilt.r
echo "Time since last = $SECONDS seconds"
SECONDS=0
