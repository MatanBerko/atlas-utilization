#!/bin/bash
# Nominal-6 additions precheck (27 Nov 2026): copy the generator cards out of the CMS gridpacks named in the McM
# fragments (read only, /cvmfs). Only small card files are extracted, into $WORK_DIR/gridpack_cards/<recid>/.
# GRIDPACKS = file with lines "<recid> <gen_prepid> <gridpack path>".
#PBS -N n6_cards
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
set -uo pipefail
W="${WORK_DIR:?WORK_DIR not set}"; G="${GRIDPACKS:?GRIDPACKS not set}"
export HOME="$W/.jobhome"; mkdir -p "$HOME" "$W/gridpack_cards"
echo "Job $PBS_JOBID on $(hostname) at $(date)"
PAT='*proc_card*.dat *run_card.dat *madspin_card*.dat *param_card.dat *customizecards*.dat *reweight_card*.dat powheg.input *JHUGen*.input *.input'
set -f   # the card patterns are for tar, never for the shell
while read -r rid pid gp; do
  d="$W/gridpack_cards/$rid"; mkdir -p "$d"
  echo "== $rid $pid $gp"; ls -l "$gp" || { echo "MISSING $gp"; continue; }
  sha256sum "$gp" > "$d/gridpack.sha256"
  case "$gp" in *.tar.xz) opt=-J ;; *.tgz|*.tar.gz) opt=-z ;; *) opt= ;; esac
  # one pass: extract only the card-like files (wildcards, any depth); --no-same-owner, never overwrite
  tar $opt -x -f "$gp" -C "$d" --wildcards --no-anchored --no-same-owner --keep-old-files $PAT 2>"$d/tar_stderr.txt"
  echo "exit $? ; $(find "$d" -type f | wc -l) files"
done < "$G"
echo "done $(date)"
