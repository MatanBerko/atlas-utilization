#!/bin/bash
# ---------------------------------------------------------------------------
# status_zee.sh
#
# Implementation task 6, Part 4: status for the Z->e+e- control-region run
# (2 array jobs -- data, DY; see submit_zee.sh -- REVISED 16 Sep 2026,
# was 4 variants before the trigger-efficiency sample became an offline
# cut instead of a separate cluster job). Same
# bulk `qstat -xft` array-status fix as status_full.sh (one call per array
# job, not one per subjob -- see that script's own header for why the
# naive per-index approach is broken on this cluster).
#
# Usage: bash status_zee.sh --mode pilot   (or --mode full)
# QSTAT_CMD can be overridden, same as status_full.sh, for the mocked test.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
ZEE_BASE="${ZEE_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_zee}"
ZEE_LOG_BASE="${ZEE_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_zee}"
QSTAT_CMD="${QSTAT_CMD:-qstat}"

MODE=""
args=("$@")
for i in "${!args[@]}"; do
    case "${args[$i]}" in
        --mode=*) MODE="${args[$i]#--mode=}" ;;
        --mode) MODE="${args[$((i+1))]:-}" ;;
    esac
done
if [[ -z "$MODE" ]]; then
    echo "Usage: bash status_zee.sh --mode pilot|full" >&2
    exit 1
fi

JOBLIST_FILE="${ZEE_LOG_BASE}/submitted_jobs_${MODE}.txt"
if [[ ! -f "$JOBLIST_FILE" ]]; then
    echo "No job list found at $JOBLIST_FILE -- has submit_zee.sh --$MODE been run?" >&2
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

check_output_exists() {
    local sel_dir="$1"
    if [[ -f "${sel_dir}/job_metadata.json" ]]; then
        echo "OK"
    else
        echo "MISSING"
    fi
}

ANY_FAILED=0

while read -r name jobid; do
    [[ -z "$name" ]] && continue
    echo "=== $name (jobid=$jobid) ==="
    QUERY_ID=$(array_query_id "$jobid")
    DUMP=$(nice "$QSTAT_CMD" -xft "$QUERY_ID" 2>/dev/null || true)
    PARSED=$(echo "$DUMP" | parse_array_dump)

    n_queued=0; n_running=0; n_ok=0; n_failed=0; n_unknown=0
    variant_base="${ZEE_BASE}/${name}"
    while read -r idx state exit_status walltime mem; do
        [[ -z "$idx" ]] && continue
        sel_dir="${variant_base}/job_${idx}/selected"
        case "$state" in
            Q) n_queued=$((n_queued+1)) ;;
            R) n_running=$((n_running+1)) ;;
            F)
                if [[ "$exit_status" == "0" ]] && [[ "$(check_output_exists "$sel_dir")" == "OK" ]]; then
                    n_ok=$((n_ok+1))
                else
                    n_failed=$((n_failed+1))
                    ANY_FAILED=1
                    echo "  index $idx: FAILED (state=$state exit_status=$exit_status wall=$walltime mem=$mem output=$(check_output_exists "$sel_dir"))"
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
else
    echo "Some subjobs failed -- see FAILED lines above. Move each failed"
    echo "job_<i> directory aside (never delete) and resubmit just that"
    echo "index with, e.g.:"
    echo "  qsub -J <i>-<i> -v CONFIG=<same config>,IS_DATA=<true|false>,TOTAL_FILES=<151 for data, 41 for DY>,OUTPUT_BASE=<same output base> studies/hgg_cms/cluster/pbs_hgg_zee_array.sh"
fi
