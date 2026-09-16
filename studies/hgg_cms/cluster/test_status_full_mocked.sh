#!/bin/bash
# ---------------------------------------------------------------------------
# test_status_full_mocked.sh
#
# Implementation task 6, Part 2: regression test for status_full.sh's data-
# array bug fix. Builds a small synthetic FULL_BASE/FULL_LOG_BASE tree (3
# data jobs + 1 signal job) and a MOCKED `qstat` script that reproduces the
# real format the bug was found against: `qstat -xft "<jobid>[].pbs"`
# returning one "Job Id: <jobid>[<i>].pbs" block per finished array subjob,
# each with job_state = F and Exit_status = 0 -- exactly the case the old
# per-index-query code misreported as "unknown=133".
#
# Self-contained: no real cluster, no real qstat, no network. Run with:
#   bash studies/hgg_cms/cluster/test_status_full_mocked.sh
# Exits 0 and prints "ALL CHECKS PASSED" on success; exits 1 with a message
# identifying which check failed otherwise.
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FULL_BASE="$TMP/output/hgg_full"
FULL_LOG_BASE="$TMP/logs/hgg_full"
mkdir -p "$FULL_BASE/data" "$FULL_BASE/signal/ggh" "$FULL_LOG_BASE"

DATA_JOBID="5045473[].pbs"
SIGNAL_JOBID="5045500.pbs"

cat > "$FULL_LOG_BASE/submitted_jobs.txt" <<EOF
data_array $DATA_JOBID
signal_ggh $SIGNAL_JOBID
EOF

# ---- 3 synthetic data jobs: each gets its own metadata_cache.json (one
# record, 3 files total -- so batching at total_batches=3 gives job i the
# i-th file, no duplicates) + a real selected/job_metadata.json + at least
# one .root file, so check_output_exists reports OK. ----
for i in 1 2 3; do
    jd="$FULL_BASE/data/job_${i}"
    mkdir -p "$jd/selected"
    cat > "$jd/metadata_cache.json" <<EOF
{"record_x": [
  "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/x/A.root",
  "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/x/B.root",
  "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/x/C.root"
]}
EOF
    echo '{"cutflow": {"n_selected": 1}}' > "$jd/selected/job_metadata.json"
    touch "$jd/selected/dummy_${i}.root"
done

mkdir -p "$FULL_BASE/signal/ggh/selected"
echo '{"cutflow": {"n_selected": 1}}' > "$FULL_BASE/signal/ggh/selected/job_metadata.json"
touch "$FULL_BASE/signal/ggh/selected/dummy.root"

# ---- Mock qstat: reproduces the real -xft array dump format (one block
# per finished subjob, job_state = F, Exit_status = 0) for the data array,
# and a plain -xf single-job dump for the signal job. ----
MOCK_QSTAT="$TMP/mock_qstat.sh"
cat > "$MOCK_QSTAT" <<'MOCKEOF'
#!/bin/bash
args="$*"
if [[ "$args" == *"-xft"* ]]; then
    for i in 1 2 3; do
        cat <<BLOCK
Job Id: 5045473[${i}].pbs
    Job_Name = hgg_data
    Job_Owner = berkom@wipp01.example
    resources_used.cput = 00:01:${i}0
    resources_used.mem = 2145996kb
    resources_used.vmem = 3200000kb
    resources_used.walltime = 00:0${i}:03
    job_state = F
    queue = N
    server = pbs
    Exit_status = 0
    ctime = Tue Sep 16 08:00:00 2026
    etime = Tue Sep 16 08:00:01 2026

BLOCK
    done
    exit 0
elif [[ "$args" == *"-xf"* ]]; then
    cat <<BLOCK
Job Id: 5045500.pbs
    Job_Name = hgg_signal
    job_state = F
    resources_used.walltime = 00:00:37
    resources_used.mem = 734000kb
    Exit_status = 0

BLOCK
    exit 0
fi
exit 1
MOCKEOF
chmod +x "$MOCK_QSTAT"

OUT="$TMP/status_output.txt"
FULL_BASE="$FULL_BASE" FULL_LOG_BASE="$FULL_LOG_BASE" JOBLIST_FILE="$FULL_LOG_BASE/submitted_jobs.txt" \
    QSTAT_CMD="$MOCK_QSTAT" PYTHON_CMD="python" TOTAL_DATA_INDICES=3 \
    bash "$HERE/status_full.sh" > "$OUT" 2>&1

echo "----- status_full.sh output -----"
cat "$OUT"
echo "----------------------------------"

fail() { echo "TEST FAILED: $1"; exit 1; }

grep -q "finished_ok=3 failed=0 unknown=0 (of 3)" "$OUT" \
    || fail "expected 'finished_ok=3 failed=0 unknown=0 (of 3)' -- the exact bug this fix targets (previously reported unknown=133/unknown=3)"

grep -q "no duplicate input files" "$OUT" \
    || fail "expected the 3 distinct reconstructed files to show no duplicates"

grep -qE "job_1: record_x -> .*/x/A\.root" "$OUT" \
    || fail "expected job_1's reconstructed file to be .../x/A.root"
grep -qE "job_3: record_x -> .*/x/C\.root" "$OUT" \
    || fail "expected job_3's reconstructed file to be .../x/C.root"

grep -q "ggh (jobid=5045500.pbs): FINISHED_OK" "$OUT" \
    || fail "expected the signal ggh job to report FINISHED_OK"

grep -q "No failures detected" "$OUT" \
    || fail "expected no failures given every mocked job is F/Exit_status=0 with real output present"

echo "ALL CHECKS PASSED"
