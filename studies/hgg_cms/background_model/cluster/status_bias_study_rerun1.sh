#!/bin/bash
# ---------------------------------------------------------------------------
# status_bias_study_rerun1.sh
#
# Background-model task, bias-study rerun 1: status for the rerun array
# job submitted by submit_bias_study_rerun1.sh. Same bulk `qstat -xft`
# array-status pattern as status_bias_study.sh / status_zee.sh.
#
# Usage: bash status_bias_study_rerun1.sh
# ---------------------------------------------------------------------------
set -euo pipefail

BIAS_OUT_BASE="${BIAS_OUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_bias/105_180_rerun1}"
BIAS_LOG_BASE="${BIAS_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_bias_rerun1}"
QSTAT_CMD="${QSTAT_CMD:-qstat}"

JOBLIST_FILE="${BIAS_LOG_BASE}/submitted_jobs.txt"
if [[ ! -f "$JOBLIST_FILE" ]]; then
    echo "No job list found at $JOBLIST_FILE -- has submit_bias_study_rerun1.sh been run?" >&2
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

ANY_FAILED=0

while read -r label jobid; do
    [[ -z "$label" ]] && continue
    echo "=== $label (jobid=$jobid) ==="
    QUERY_ID=$(array_query_id "$jobid")
    DUMP=$(nice "$QSTAT_CMD" -xft "$QUERY_ID" 2>/dev/null || true)
    PARSED=$(echo "$DUMP" | parse_array_dump)

    n_queued=0; n_running=0; n_ok=0; n_failed=0; n_unknown=0
    JOB_LIST="${BIAS_LOG_BASE}/job_list_105_180_rerun1.txt"
    while read -r idx state exit_status walltime mem; do
        [[ -z "$idx" ]] && continue
        line=$(sed -n "${idx}p" "$JOB_LIST" 2>/dev/null || true)
        read -r category truth_family leakage_variant mass _n_toys _seed test_function <<< "$line"
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
                    echo "  index $idx ($category/$truth_family/$leakage_variant/m$mass, $test_function): FAILED (state=$state exit_status=$exit_status wall=$walltime mem=$mem output=$([[ -f "$out_file" ]] && echo OK || echo MISSING))"
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
    echo "Once all 120 subjobs show finished_ok, merge with:"
    echo "  python studies/hgg_cms/background_model/cluster/merge_bias_results.py \\"
    echo "      --fit-range 105_180 \\"
    echo "      --extra-jobs-dir /storage/agrp/berkom/atlas-utilization/output/hgg_bias/105_180_rerun1 \\"
    echo "      --out /storage/agrp/berkom/atlas-utilization/output/hgg_bias/merged/bias_study_105_180_with_rerun1.json"
else
    echo "Some subjobs failed -- see FAILED lines above. Resubmit just that"
    echo "index with, e.g.:"
    echo "  qsub -J <idx>-<idx> -v JOB_LIST=<same job list>,OUT_BASE=<same out base>,LEAKAGE_JSON=<same leakage json> studies/hgg_cms/background_model/cluster/pbs_hgg_bias_rerun1_array.sh"
fi
