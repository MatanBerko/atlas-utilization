#!/bin/bash
# Full run 25 Oct 2026, step 4: a dummy job for testing the OpenPBS
# dependency syntax on arrays. Does nothing but print and exit; the subjob
# whose index equals FAIL_INDEX (if set) exits 1.
#PBS -S /bin/bash
#PBS -q N
#PBS -m n
#PBS -l select=1:ncpus=1:mem=100mb
#PBS -l walltime=00:05:00
#PBS -l io=1
echo "dummy ${PBS_JOBNAME} ${PBS_JOBID} idx=${PBS_ARRAY_INDEX:-none} host=$(hostname) $(date +%T)"
sleep "${SLEEP:-20}"
if [[ -n "${FAIL_INDEX:-}" && "${PBS_ARRAY_INDEX:-x}" == "$FAIL_INDEX" ]]; then
    echo "failing on purpose"; exit 1
fi
exit 0
