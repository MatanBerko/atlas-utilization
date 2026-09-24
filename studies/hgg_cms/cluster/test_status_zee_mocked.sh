#!/bin/bash
# ---------------------------------------------------------------------------
# test_status_zee_mocked.sh
#
# Implementation task 6, Part 4: regression test for status_zee.sh, same
# mocked-qstat approach as test_status_full_mocked.sh. Builds a tiny
# 2-subjob "pilot" job list (one data-variant array job) with a mocked
# qstat reproducing the real finished-array-subjob format.
#
# Run with: bash studies/hgg_cms/cluster/test_status_zee_mocked.sh
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

ZEE_BASE="$TMP/output/hgg_zee"
ZEE_LOG_BASE="$TMP/logs/hgg_zee"
mkdir -p "$ZEE_BASE/data_pilot" "$ZEE_LOG_BASE"

JOBID="6000001[].pbs"
cat > "$ZEE_LOG_BASE/submitted_jobs_pilot.txt" <<EOF
data_pilot $JOBID
EOF

for i in 1 2; do
    jd="$ZEE_BASE/data_pilot/job_${i}/selected"
    mkdir -p "$jd"
    echo '{"cutflow": {"n_selected": 1}}' > "$jd/job_metadata.json"
done

MOCK_QSTAT="$TMP/mock_qstat.sh"
cat > "$MOCK_QSTAT" <<'MOCKEOF'
#!/bin/bash
if [[ "$*" == *"-xft"* ]]; then
    for i in 1 2; do
        cat <<BLOCK
Job Id: 6000001[${i}].pbs
    Job_Name = hgg_zee
    job_state = F
    resources_used.walltime = 00:0${i}:15
    resources_used.mem = 1200000kb
    Exit_status = 0

BLOCK
    done
    exit 0
fi
exit 1
MOCKEOF
chmod +x "$MOCK_QSTAT"

OUT="$TMP/out.txt"
ZEE_BASE="$ZEE_BASE" ZEE_LOG_BASE="$ZEE_LOG_BASE" QSTAT_CMD="$MOCK_QSTAT" \
    bash "$HERE/status_zee.sh" --mode pilot > "$OUT" 2>&1

echo "----- status_zee.sh output -----"
cat "$OUT"
echo "---------------------------------"

fail() { echo "TEST FAILED: $1"; exit 1; }

grep -q "queued=0 running=0 finished_ok=2 failed=0 unknown=0" "$OUT" \
    || fail "expected both subjobs to report finished_ok"
grep -q "No failures detected" "$OUT" \
    || fail "expected no failures given both mocked jobs are F/Exit_status=0 with real output present"

echo "ALL CHECKS PASSED"
