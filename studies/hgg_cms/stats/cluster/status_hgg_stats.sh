#!/bin/bash
# ---------------------------------------------------------------------------
# status_hgg_stats.sh
#
# Statistical-model task: status for the toy-validation array job
# submitted by submit_hgg_stats.sh. Same bulk `qstat -xft` array-status
# pattern as studies/hgg_cms/background_model/cluster/status_bias_study_part4.sh.
#
# RETRY LIST: if any subjob is FAILED, this script builds
# <log-base>/job_list_retry<N>.txt containing ONLY the job-list lines for
# the failed indices, and prints the exact qsub command to resubmit
# them. Each failed line is printed as "  index <idx> (...): FAILED ..."
# -- that exact prefix identifies a failure line.
#
# Usage: bash status_hgg_stats.sh
# ---------------------------------------------------------------------------
set -euo pipefail

STATS_OUT_BASE="${STATS_OUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_stats}"
STATS_LOG_BASE="${STATS_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_stats}"
QSTAT_CMD="${QSTAT_CMD:-qstat}"

JOBLIST_FILE="${STATS_LOG_BASE}/submitted_jobs.txt"
if [[ ! -f "$JOBLIST_FILE" ]]; then
    echo "No job list found at $JOBLIST_FILE -- has submit_hgg_stats.sh been run?" >&2
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

next_retry_number() {
    local n=1
    while [[ -f "${STATS_LOG_BASE}/job_list_retry${n}.txt" ]]; do
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
    JOB_LIST="${STATS_LOG_BASE}/job_list.txt"
    while read -r idx state exit_status walltime mem; do
        [[ -z "$idx" ]] && continue
        line=$(sed -n "${idx}p" "$JOB_LIST" 2>/dev/null || true)
        read -r job_type mu_true n_toys _seed <<< "$line"
        out_file="${STATS_OUT_BASE}/${job_type}/job_$(printf '%04d' "$idx").json"
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
                    echo "  index $idx ($job_type mu_true=$mu_true n_toys=$n_toys): FAILED (state=$state exit_status=$exit_status wall=$walltime mem=$mem output=$([[ -f "$out_file" ]] && echo OK || echo MISSING))"
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
    echo "Once all 80 subjobs show finished_ok, merge with:"
    echo "  python studies/hgg_cms/stats/cluster/merge_hgg_stats.py \\"
    echo "      --jobs-base $STATS_OUT_BASE \\"
    echo "      --out /storage/agrp/berkom/atlas-utilization/output/hgg_stats/merged/hgg_stats_merged.json"
else
    RETRY_N=$(next_retry_number)
    RETRY_LIST="${STATS_LOG_BASE}/job_list_retry${RETRY_N}.txt"
    JOB_LIST="${STATS_LOG_BASE}/job_list.txt"
    : > "$RETRY_LIST"
    for idx in "${FAILED_IDX[@]}"; do
        sed -n "${idx}p" "$JOB_LIST" >> "$RETRY_LIST"
    done
    N_RETRY=$(wc -l < "$RETRY_LIST")
    echo "Some subjobs failed -- see FAILED lines above."
    echo "Retry list written: $RETRY_LIST ($N_RETRY line(s), same seeds as the original)."
    echo ""
    echo "If the failures were walltime kills (exit -29), especially for mass_scan_bkg (the most"
    echo "expensive job_type): this script's own PBS job already requests the maximum walltime"
    echo "(02:00:00) that still routes to the shortE queue -- a further increase routes to normE"
    echo "instead (busier; see studies/hgg_cms/cluster/FULL_RUN_README.md). Resubmit the retry list,"
    echo "reading its own job list positionally (index 1..N of the RETRY file):"
    echo "  qsub -J 1-${N_RETRY} -v JOB_LIST=$RETRY_LIST,OUT_BASE=$STATS_OUT_BASE \\"
    echo "      -l walltime=03:00:00 \\"
    echo "      studies/hgg_cms/stats/cluster/pbs_hgg_stats_array.sh"
    echo "(walltime override above via -l on the qsub command line, accepting normE routing --"
    echo "only if the failures really are walltime kills; check wall= in the FAILED lines above first.)"
fi
