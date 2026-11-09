# The exact commands run on wipp-home (ssh wipp-home 'bash -l -s' < this) on 9 Nov 2026: the log swap approved by
# Matan (9 Nov) for the 93 subjobs retried on 5 Nov. For each (record, array index) in
# $W/evidence/retry_20261105_submitted.txt:
#   1. check: f_<i>_retry1.err says "Exit status: 0", f_<i>_retry1.out ends with the normal "finished at" line,
#      f_<i>.err is the failed attempt (non-zero exit AND the portal 504 message), the destination does not exist;
#   2. MOVE the failed attempt's f_<i>.out and f_<i>.err to $W/logs_failed_20261104_portal504/<record>/ (same names);
#   3. COPY (cp -p, never overwriting) f_<i>_retry1.{out,err} to f_<i>.{out,err}; the _retry1 files stay in place.
# Nothing is deleted. Output: logswap_20261109.txt (every move and copy, source -> destination).
set -euo pipefail
W=/storage/agrp/berkom/atlas-utilization/work/mcexp_20261103/full
S=$W/evidence/retry_20261105_submitted.txt; F=$W/logs_failed_20261104_portal504
test ! -e $F
n=$(wc -l < $S); echo "pairs in retry_20261105_submitted.txt: $n"; test "$n" -eq 93
# pass 1: check everything before touching anything
while read r job one wt tag ai fi; do
  i=${ai#array_index=}; L=$W/logs/$r
  grep -q "Exit status: 0" $L/f_${i}_retry1.err && grep -q "finished at" $L/f_${i}_retry1.out
  grep -q "Exit status: 1" $L/f_$i.err && grep -q "504 Server Error" $L/f_$i.err && test -f $L/f_$i.out
done < $S
echo "pass 1 OK: 93 retry logs exit 0 + normal end; 93 original logs are the failed 504 attempt"
mkdir -p $F; nm=0; nc=0
while read r job one wt tag ai fi; do
  i=${ai#array_index=}; L=$W/logs/$r; mkdir -p $F/$r
  for x in out err; do
    test ! -e $F/$r/f_$i.$x; mv -n $L/f_$i.$x $F/$r/f_$i.$x; test -f $F/$r/f_$i.$x && test ! -e $L/f_$i.$x
    echo "MOVE $L/f_$i.$x -> $F/$r/f_$i.$x"
  done; nm=$((nm+1))
  for x in out err; do
    cp -p -n $L/f_${i}_retry1.$x $L/f_$i.$x; cmp -s $L/f_${i}_retry1.$x $L/f_$i.$x
    echo "COPY $L/f_${i}_retry1.$x -> $L/f_$i.$x"
  done; nc=$((nc+1))
done < $S
echo "moved: $nm attempts ($(find $F -type f | wc -l) files); copied: $nc attempts"
echo "retry1 files still in place: $(ls $W/logs/*/f_*_retry1.* | wc -l)"
date
