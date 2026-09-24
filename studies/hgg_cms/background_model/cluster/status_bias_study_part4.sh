#!/bin/bash
# ---------------------------------------------------------------------------
# status_bias_study_part4.sh
#
# Background-model task, Part 4: status for the 110-180 GeV robustness
# array job submitted by submit_bias_study_part4.sh. Same bulk
# `qstat -xft` array-status pattern as status_bias_study.sh /
# status_bias_study_rerun1.sh.
#
# RETRY LIST: if any subjob is FAILED, this script builds
# <log-base>/job_list_retry<N>.txt containing ONLY the job-list lines
# for the failed indices (same seeds, same test-functions -- nothing
# about the computation changes, only that these specific lines get
# resubmitted), and prints the exact qsub command to resubmit them.
# Each failed line is printed as "  index <idx> (...): FAILED ..." --
# that exact prefix is what identifies a failure line, whether read
# live from this script's own output or pasted back later.
#
# Usage: bash status_bias_study_part4.sh
# ---------------------------------------------------------------------------
set -euo pipefail

BIAS_OUT_BASE="${BIAS_OUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_bias/110_180_part4}"
BIAS_LOG_BASE="${BIAS_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_bias_part4}"
QSTAT_CMD="${QSTAT_CMD:-qstat}"

JOBLIST_FILE="${BIAS_LOG_BASE}/submitted_jobs.txt"
if [[ ! -f "$JOBLIST_FILE" ]]; then
    echo "No job list found at $JOBLIST_FILE -- has submit_bias_study_part4.sh been run?" >&2
    exit 1
fi

parse_array_dump() {
    awk '
        function flush() {
            if (idx != "") printf "%s %s %s %s %s\n", idx, (state=="" ? "UNKNOWN" : state), \
                (exit_status=="" ? "." : exit_status), (walltime=="" ? "." : walltime), \
                (mem=="" ? "." : mem)
        }
        /^Job Id: / {
            flush()
            idx = ""
            if (match($0, /\[[0-9]+\]/)) { idx = substr($0, RSTART + 1, RLENGTH - 2) }
            state = ""; exit_status = ""; walltime = ""; mem = ""
            next
        }
        {
            line = $0
            sub(/^[ \t]+/, "", line)
            sub(/[\r\n]+$/, "", line)
            if (line ~ /^job_state = /) { state = substr(line, index(line, "=") + 2) }
            else if (line ~ /^Exit_status = /) { exit_status = substr(line, index(line, "=") + 2) }
            else if (line ~ /^resources_used\.walltime = /) { walltime = substr(line, index(line, "=") + 2) }
            else if (line ~ /^resources_used\.mem = /) { mem = substr(line, index(line, "=") + 2) }
        }
        END { flush() }
    '
}

array_query_id() {
    local jobid="$1"
    if [[ "$jobid" == *"[]"* ]]; then
        echo "$jobid"
    elif [[ "$jobid" == *.* ]]; then
        echo "${jobid%%.*}[].${jobid#*.}"
    else
        echo "${jobid}[]"
    fi
}

# Find the next unused retry-list number so repeated runs of this script
# don't clobber an earlier retry list.
next_retry_number() {
    local n=1
    while [[ -f "${BIAS_LOG_BASE}/job_list_retry${n}.txt" ]]; do
        n=$((n+1))
    done
    echo "$n"
}

ANY_FAILED=0
declare -a FAILED_IDX=()

while read -r label jobid; do
    [[ -z "$label" ]] && continue
    echo "=== $label (jobid=$jobid) ==="
    QUERY_ID=$(array_query_id "$jobid")
    DUMP=$(nice "$QSTAT_CMD" -xft "$QUERY_ID" 2>/dev/null || true)
    PARSED=$(echo "$DUMP" | parse_array_dump)

    n_queued=0; n_running=0; n_ok=0; n_failed=0; n_unknown=0
    JOB_LIST="${BIAS_LOG_BASE}/job_list_110_180_part4.txt"
    while read -r idx state exit_status walltime mem; do
        [[ -z "$idx" ]] && continue
        line=$(sed -n "${idx}p" "$JOB_LIST" 2>/dev/null || true)
        read -r category truth_family leakage_variant mass _n_toys _seed test_functions <<< "$line"
        out_file="${BIAS_OUT_BASE}/${category}_${truth_family}_${leakage_variant}_m${mass}.json"
        case "$state" in
            Q) n_queued=$((n_queued+1)) ;;
            R) n_running=$((n_running+1)) ;;
            F)
                if [[ "$exit_status" == "0" ]] && [[ -f "$out_file" ]]; then
                    n_ok=$((n_ok+1))
                else
                    n_failed=$((n_failed+1))
                    ANY_FAILED=1
                    FAILED_IDX+=("$idx")
                    echo "  index $idx ($category/$truth_family/$leakage_variant/m$mass, $test_functions): FAILED (state=$state exit_status=$exit_status wall=$walltime mem=$mem output=$([[ -f "$out_file" ]] && echo OK || echo MISSING))"
                fi
                ;;
            *) n_unknown=$((n_unknown+1)) ;;
        esac
    done <<< "$PARSED"
    echo "  queued=$n_queued running=$n_running finished_ok=$n_ok failed=$n_failed unknown=$n_unknown"
    echo ""
done < "$JOBLIST_FILE"

echo "=== Summary ==="
if [[ "$ANY_FAILED" == "0" ]]; then
    echo "No failures detected (among jobs currently in a finished state)."
    echo "Once all 8 subjobs show finished_ok, merge with (the primary <out-base>/110_180/ source is"
    echo "empty/nonexistent on purpose -- Part 4 has no 'first run' to combine with, so all of this"
    echo "run's output comes from --extra-jobs-dir; glob() on a nonexistent primary dir is harmless):"
    echo "  python studies/hgg_cms/background_model/cluster/merge_bias_results.py \\"
    echo "      --fit-range 110_180 --out-base /storage/agrp/berkom/atlas-utilization/output/hgg_bias \\"
    echo "      --extra-jobs-dir $BIAS_OUT_BASE \\"
    echo "      --order-selection-json studies/hgg_cms/background_model/results/order_selection_110_180.json \\"
    echo "      --out /storage/agrp/berkom/atlas-utilization/output/hgg_bias/merged/bias_study_110_180_part4.json"
else
    RETRY_N=$(next_retry_number)
    RETRY_LIST="${BIAS_LOG_BASE}/job_list_retry${RETRY_N}.txt"
    JOB_LIST="${BIAS_LOG_BASE}/job_list_110_180_part4.txt"
    : > "$RETRY_LIST"
    # Build the retry list from ONLY the failed indices -- same seeds,
    # same test-functions, nothing about the computation changes.
    for idx in "${FAILED_IDX[@]}"; do
        sed -n "${idx}p" "$JOB_LIST" >> "$RETRY_LIST"
    done
    N_RETRY=$(wc -l < "$RETRY_LIST")
    echo "Some subjobs failed -- see FAILED lines above."
    echo "Retry list written: $RETRY_LIST ($N_RETRY line(s), same seeds/test-functions as the original)."
    echo ""
    echo "If the failures were walltime kills (exit -29, like rerun 1's notEBEB bernstein_7 cells):"
    echo "this script's own PBS job (pbs_hgg_bias_part4_array.sh) already requests the maximum"
    echo "walltime (02:00:00) that still routes to the shortE queue -- a further increase routes to"
    echo "normE instead (busier; see FULL_RUN_README.md). Resubmit the retry list, reading its own"
    echo "job list positionally (index 1..N of the RETRY file, not the original indices):"
    echo "  qsub -J 1-${N_RETRY} -v JOB_LIST=$RETRY_LIST,OUT_BASE=$BIAS_OUT_BASE,LEAKAGE_JSON=<same leakage json> \\"
    echo "      -l walltime=03:00:00 \\"
    echo "      studies/hgg_cms/background_model/cluster/pbs_hgg_bias_part4_array.sh"
    echo "(walltime override above via -l on the qsub command line, accepting normE routing --"
    echo "only if the failures really are walltime kills; check wall= in the FAILED lines above first.)"
fi
