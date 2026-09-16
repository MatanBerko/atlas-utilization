#!/bin/bash
# ---------------------------------------------------------------------------
# status_full.sh
#
# Summarizes the full H->gamma-gamma run's jobs, reading job IDs from a
# submitted_jobs.txt file (one "name jobid" pair per line -- exactly what
# submit_full.sh writes to logs/hgg_full/submitted_jobs.txt). Meant to run
# on the analysis node, under `nice`, and finish in seconds -- it only
# calls `qstat` (fast) and stats a handful of files per job, never reads
# or opens any actual ROOT/data file.
#
# For the data array job (one entry, "data_array <jobid>"), every one of
# the 133 subjob indices is queried individually
# (`qstat -xf "<jobid>[<index>]"`) -- OpenPBS's bulk "<jobid>[]" query
# does not reliably return full per-subjob resource-usage fields across
# all site configurations (UNVERIFIED on this specific cluster -- no
# access to test it), so the per-index loop is used instead for
# correctness. 133 small, fast qstat calls should still be well under a
# minute in total on a responsive scheduler; if it is not, see this
# file's own comments near QSTAT_BULK_ARRAY_QUERY for the (unverified,
# untested) bulk-query alternative to try.
#
# For each finished job/subjob (job_state F, i.e. -x's historical-jobs
# view), this ALSO checks that its expected output actually exists
# (selected/job_metadata.json, at least one *.root file under selected/)
# -- an exit code of 0 with no such output is flagged FAILED, not OK,
# since a job can exit cleanly and still have produced nothing useful
# (e.g. an empty chunk list).
#
# QSTAT_CMD can be overridden (default: "qstat") -- used by this task's
# own test to point at a mocked qstat script instead of the real one; see
# studies/hgg_cms/impl_checks/mapping_check/ sibling test docs / the final
# report for that mocked run's own labeled output.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
FULL_BASE="${FULL_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_full}"
FULL_LOG_BASE="${FULL_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_full}"
JOBLIST_FILE="${JOBLIST_FILE:-${FULL_LOG_BASE}/submitted_jobs.txt}"
QSTAT_CMD="${QSTAT_CMD:-qstat}"
TOTAL_DATA_INDICES="${TOTAL_DATA_INDICES:-133}"

if [[ ! -f "$JOBLIST_FILE" ]]; then
    echo "No job list found at $JOBLIST_FILE -- has submit_full.sh been run?" >&2
    exit 1
fi

# ---- qstat -f field extraction (tolerant of leading whitespace / line
# wrapping -- standard OpenPBS field names, but exact formatting can vary
# by site/version, so this greps for "key = value" rather than assuming
# fixed columns). ----
qstat_field() {
    # qstat_field "<qstat -f output>" "<field name>"
    echo "$1" | grep -E "^ *$2 = " | head -1 | sed -E "s/^ *$2 = //"
}

query_one() {
    # query_one "<pbs id, e.g. 12345[7] or 12345>" -> prints
    # "STATE EXIT_STATUS WALLTIME MEM" (fields empty if unknown/not finished)
    local pbsid="$1"
    local out
    if ! out=$(nice "$QSTAT_CMD" -xf "$pbsid" 2>/dev/null); then
        echo "UNKNOWN . . ."
        return
    fi
    local state exit_status walltime mem
    state=$(qstat_field "$out" "job_state")
    exit_status=$(qstat_field "$out" "Exit_status")
    walltime=$(qstat_field "$out" "resources_used.walltime")
    mem=$(qstat_field "$out" "resources_used.mem")
    echo "${state:-UNKNOWN} ${exit_status:-.} ${walltime:-.} ${mem:-.}"
}

check_output_exists() {
    # check_output_exists "<selected-dir>" -> "OK" or "MISSING"
    local sel_dir="$1"
    if [[ -f "${sel_dir}/job_metadata.json" ]] && compgen -G "${sel_dir}/*.root" > /dev/null; then
        echo "OK"
    else
        echo "MISSING"
    fi
}

FAILED_DATA_INDICES=()
FAILED_SIGNAL_LABELS=()

echo "=== DATA array ==="
DATA_JOBID=$(awk '$1=="data_array"{print $2}' "$JOBLIST_FILE")
if [[ -z "$DATA_JOBID" ]]; then
    echo "  (no data_array entry in $JOBLIST_FILE)"
else
    n_queued=0; n_running=0; n_ok=0; n_failed=0; n_unknown=0
    for i in $(seq 1 "$TOTAL_DATA_INDICES"); do
        read -r state exit_status walltime mem <<< "$(query_one "${DATA_JOBID}[${i}]")"
        sel_dir="${FULL_BASE}/data/job_${i}/selected"
        case "$state" in
            Q) n_queued=$((n_queued+1)) ;;
            R) n_running=$((n_running+1)) ;;
            F)
                if [[ "$exit_status" == "0" ]] && [[ "$(check_output_exists "$sel_dir")" == "OK" ]]; then
                    n_ok=$((n_ok+1))
                else
                    n_failed=$((n_failed+1))
                    FAILED_DATA_INDICES+=("$i")
                    echo "  index $i: FAILED (state=$state exit_status=$exit_status wall=$walltime mem=$mem output=$(check_output_exists "$sel_dir"))"
                fi
                ;;
            *) n_unknown=$((n_unknown+1)) ;;
        esac
    done
    echo "  jobid=$DATA_JOBID: queued=$n_queued running=$n_running finished_ok=$n_ok failed=$n_failed unknown=$n_unknown (of $TOTAL_DATA_INDICES)"
fi

echo ""
echo "=== SIGNAL jobs ==="
while read -r name jobid; do
    [[ "$name" == data_array ]] && continue
    [[ -z "$name" ]] && continue
    label="${name#signal_}"
    read -r state exit_status walltime mem <<< "$(query_one "$jobid")"
    sel_dir="${FULL_BASE}/signal/${label}/selected"
    status="UNKNOWN"
    case "$state" in
        Q) status="QUEUED" ;;
        R) status="RUNNING" ;;
        F)
            if [[ "$exit_status" == "0" ]] && [[ "$(check_output_exists "$sel_dir")" == "OK" ]]; then
                status="FINISHED_OK"
            else
                status="FAILED"
                FAILED_SIGNAL_LABELS+=("$label")
            fi
            ;;
    esac
    echo "  $label (jobid=$jobid): $status (state=$state exit_status=$exit_status wall=$walltime mem=$mem output=$(check_output_exists "$sel_dir"))"
done < "$JOBLIST_FILE"

echo ""
echo "=== Summary ==="
if [[ ${#FAILED_DATA_INDICES[@]} -eq 0 && ${#FAILED_SIGNAL_LABELS[@]} -eq 0 ]]; then
    echo "No failures detected (among jobs currently in a finished state)."
else
    echo "Failed data indices: ${FAILED_DATA_INDICES[*]:-none}"
    echo "Failed signal labels: ${FAILED_SIGNAL_LABELS[*]:-none}"
    echo ""
    echo "--- Resubmit commands (run these yourself, on the cluster) ---"
    TS='$(date +%Y%m%d_%H%M%S)'
    if [[ ${#FAILED_DATA_INDICES[@]} -gt 0 ]]; then
        echo "# Move each failed data index's output/logs aside first (never delete):"
        for i in "${FAILED_DATA_INDICES[@]}"; do
            echo "TS=$TS; mv ${FULL_BASE}/data/job_${i} ${FULL_BASE}/data/job_${i}_failed1_\${TS} 2>/dev/null"
        done
        echo "# Then resubmit just these indices. OpenPBS's -J start-end accepts a"
        echo "# single-element range (start==end) on most sites -- UNVERIFIED on this"
        echo "# specific cluster; if it's rejected, use the -v PBS_ARRAY_INDEX fallback"
        echo "# instead (also shown), which does not depend on that support at all:"
        for i in "${FAILED_DATA_INDICES[@]}"; do
            echo "qsub -J ${i}-${i} -v OUTPUT_BASE=${FULL_BASE}/data -o ${FULL_LOG_BASE}/data/hgg_data_full_${i}_retry.out -e ${FULL_LOG_BASE}/data/hgg_data_full_${i}_retry.err studies/hgg_cms/cluster/pbs_hgg_data_array.sh"
            echo "# fallback if -J ${i}-${i} is rejected:"
            echo "# qsub -v PBS_ARRAY_INDEX=${i},OUTPUT_BASE=${FULL_BASE}/data -o ${FULL_LOG_BASE}/data/hgg_data_full_${i}_retry.out -e ${FULL_LOG_BASE}/data/hgg_data_full_${i}_retry.err studies/hgg_cms/cluster/pbs_hgg_data_array.sh"
        done
    fi
    if [[ ${#FAILED_SIGNAL_LABELS[@]} -gt 0 ]]; then
        echo "# Move each failed signal label's output/logs aside first (never delete):"
        for label in "${FAILED_SIGNAL_LABELS[@]}"; do
            echo "TS=$TS; mv ${FULL_BASE}/signal/${label} ${FULL_BASE}/signal/${label}_failed1_\${TS} 2>/dev/null"
        done
        echo "# Then resubmit just these records:"
        for label in "${FAILED_SIGNAL_LABELS[@]}"; do
            echo "qsub -v CONFIG=config.cms_hgg_signal_${label}.yaml,LABEL=${label}_full_retry,OUTPUT_BASE=${FULL_BASE}/signal/${label} -o ${FULL_LOG_BASE}/signal/hgg_signal_${label}_full_retry.out -e ${FULL_LOG_BASE}/signal/hgg_signal_${label}_full_retry.err studies/hgg_cms/cluster/pbs_hgg_signal.sh"
        done
    fi
fi
