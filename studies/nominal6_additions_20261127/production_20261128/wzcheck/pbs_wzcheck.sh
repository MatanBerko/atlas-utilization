#!/bin/bash
# D-WZ check (28 Nov 2026): (1) read the generator cards inside the gridpacks of the WZ+2j EW candidates 72728 and 72720
# (read only, /cvmfs). The archive is LISTED first; only exact card paths at the top levels are then streamed out with
# tar -xO into flat file names (no directories are created: lesson of 27 Nov). (2) gen_check.py (the fixed 27 Nov
# version, root:// as the driver) on file 0 of each candidate: fraction of events with a generator top quark.
#PBS -N n6_wz
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
set -uo pipefail
W="${WORK_DIR:?}"; R="${REPO_DIR:?}"
export HOME="$W/.jobhome" MPLCONFIGDIR="$W/.mplconfig" XDG_CACHE_HOME="$W/.cache" OMP_NUM_THREADS=1
mkdir -p "$HOME" "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$W/cards" "$W/gen_check"
echo "Job $PBS_JOBID on $(hostname) at $(date); repo commit $(git -C "$R" rev-parse HEAD)"
while read -r rid gp; do
  echo "== $rid $gp"; sha256sum "$gp" > "$W/cards/${rid}__gridpack.sha256"
  tar -tJf "$gp" > "$W/cards/${rid}__listing.txt"
  grep -E '^(\./)?(InputCards/[^/]+|process/Cards/(proc_card_mg5|run_card|madspin_card|param_card)\.dat|process/madspin_param_card\.dat|[^/]+_(proc|run|madspin|customize)_?cards?\.dat)$' \
       "$W/cards/${rid}__listing.txt" | while read -r f; do
    tar -xJOf "$gp" "$f" > "$W/cards/${rid}__$(echo "$f" | sed 's|^\./||; s|/|__|g')"; echo "  $f"; done
done < "$W/gridpacks_wz.txt"
source /usr/wipp/conda/24.5.0/etc/profile.d/conda.sh
conda activate /storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline
/usr/bin/time -v python -u "$W/gen_check.py" --repo "$R" --max-events 100000 --out "$W/gen_check" --records 72728 72720
echo "done $(date)"
