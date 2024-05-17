#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --partition=lin-kp
#SBATCH --account=lin-kp
#SBATCH --time=100:00:00
#SBATCH -o /uufs/chpc.utah.edu/common/home/u0890904/LAIR_1/Atmos_Column/slurm/logs/%A.out

SECONDS=0
echo "
-----------------------------
"
echo $(which R)
echo "Rscript /uufs/chpc.utah.edu/common/home/lin-group15/agm/STILT_runs/test2/20230707/r/ac_run_stilt.r"
Rscript /uufs/chpc.utah.edu/common/home/lin-group15/agm/STILT_runs/test2/20230707/r/ac_run_stilt.r
echo "Time since last = $SECONDS seconds"
SECONDS=0
