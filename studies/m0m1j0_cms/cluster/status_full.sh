#!/bin/bash
# ---------------------------------------------------------------------------
# status_full.sh
#
# Summarizes the m0m1j0 full-run job array's status, reading the job id
# and total job count from submitted_jobs.txt (written by submit_full.sh:
# "m0m1j0_full <jobid> <total_jobs>"). Mirrors the pilot's own
# status_pilot.sh / the hgg_cms study's status_full.sh qstat-parsing
# approach (bulk `qstat -xft "<array-id>[]..."` call, awk-parsed, PBS
# Pro's own "[]"-suffixed array jobid).
#
# Login shells on this cluster are zsh, where an unquoted "[...]" in a
# job id is glob-expanded -- every qstat/job-id argument here is
# double-quoted for exactly that reason.
#
# For each finished subjob, also checks that its expected output
# (job_metadata.json + all_histograms.root + dimuon_diagnostics.npz under
# job_<i>/) actually exists -- exit code 0 with no such output is FAILED.
#
# QSTAT_CMD can be overridden (default: "qstat") for testing against a
# mocked qstat script.
# ---------------------------------------------------------------------------
set -euo pipefail

FULL_OUTPUT_BASE="${FULL_OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_full}"
FULL_LOG_BASE="${FULL_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/m0m1j0_full}"
JOBLIST_FILE="${JOBLIST_FILE:-${FULL_LOG_BASE}/submitted_jobs.txt}"
QSTAT_CMD="${QSTAT_CMD:-qstat}"

if [[ ! -f "$JOBLIST_FILE" ]]; then
    echo "No job list found at $JOBLIST_FILE -- has submit_full.sh been run?" >&2
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
            if (match($0, /\[[0-9]+\]/)) {
                idx = substr($0, RSTART + 1, RLENGTH - 2)
            }
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
    local job_dir="$1"
    if [[ -f "${job_dir}/job_metadata.json" ]] && [[ -f "${job_dir}/all_histograms.root" ]] \
       && [[ -f "${job_dir}/dimuon_diagnostics.npz" ]]; then
        echo "OK"
    else
        echo "MISSING"
    fi
}

read -r _NAME JOBID TOTAL_JOBS < <(awk '$1=="m0m1j0_full"{print; exit}' "$JOBLIST_FILE")
if [[ -z "${JOBID:-}" ]]; then
    echo "  (no m0m1j0_full entry in $JOBLIST_FILE)" >&2
    exit 1
fi

echo "=== m0m1j0 full-run array (jobid=$JOBID, $TOTAL_JOBS expected jobs) ==="
QUERY_ID=$(array_query_id "$JOBID")
echo "  querying: nice $QSTAT_CMD -xft \"$QUERY_ID\""
DUMP=$(nice "$QSTAT_CMD" -xft "$QUERY_ID" 2>/dev/null || true)
PARSED=$(echo "$DUMP" | parse_array_dump)

n_queued=0; n_running=0; n_ok=0; n_failed=0; n_unknown=0
FAILED_INDICES=()
declare -A SEEN_INDEX=()
while read -r idx state exit_status walltime mem; do
    [[ -z "$idx" ]] && continue
    SEEN_INDEX["$idx"]=1
    job_dir="${FULL_OUTPUT_BASE}/job_${idx}"
    case "$state" in
        Q) n_queued=$((n_queued+1)) ;;
        R) n_running=$((n_running+1)) ;;
        F)
            if [[ "$exit_status" == "0" ]] && [[ "$(check_output_exists "$job_dir")" == "OK" ]]; then
                n_ok=$((n_ok+1))
            else
                n_failed=$((n_failed+1))
                FAILED_INDICES+=("$idx")
                echo "  index $idx: FAILED (state=$state exit_status=$exit_status wall=$walltime mem=$mem output=$(check_output_exists "$job_dir"))"
            fi
            ;;
        *) n_unknown=$((n_unknown+1)) ;;
    esac
done <<< "$PARSED"

for i in $(seq 1 "$TOTAL_JOBS"); do
    if [[ -z "${SEEN_INDEX[$i]:-}" ]]; then
        n_unknown=$((n_unknown+1))
        echo "  index $i: UNKNOWN (no qstat record found)"
    fi
done

echo ""
echo "queued=$n_queued running=$n_running finished_ok=$n_ok failed=$n_failed unknown=$n_unknown (of $TOTAL_JOBS)"

echo ""
echo "=== Summary ==="
if [[ ${#FAILED_INDICES[@]} -eq 0 && $n_unknown -eq 0 ]]; then
    echo "No failures detected, no unknown indices -- all $TOTAL_JOBS accounted for."
else
    if [[ ${#FAILED_INDICES[@]} -gt 0 ]]; then
        echo "Failed indices: ${FAILED_INDICES[*]}"
        echo ""
        echo "--- Retry commands (only the missing/failed indices, larger walltime per this task's own retry rule) ---"
        TS='$(date +%Y%m%d_%H%M%S)'
        for i in "${FAILED_INDICES[@]}"; do
            echo "TS=$TS; mv ${FULL_OUTPUT_BASE}/job_${i} ${FULL_OUTPUT_BASE}/job_${i}_failed1_\${TS} 2>/dev/null"
            echo "qsub -J ${i}-${i} -l walltime=00:40:00 -v OUTPUT_BASE=${FULL_OUTPUT_BASE},REPO_DIR=\$REPO_DIR,MAPPING_FILE=${FULL_OUTPUT_BASE}/job_index_map.txt -o ${FULL_LOG_BASE}/m0m1j0_full_${i}_retry.out -e ${FULL_LOG_BASE}/m0m1j0_full_${i}_retry.err studies/m0m1j0_cms/cluster/pbs_m0m1j0_full.sh"
            echo "# fallback if -J ${i}-${i} is rejected:"
            echo "# qsub -v PBS_ARRAY_INDEX=${i},OUTPUT_BASE=${FULL_OUTPUT_BASE},REPO_DIR=\$REPO_DIR,MAPPING_FILE=${FULL_OUTPUT_BASE}/job_index_map.txt -l walltime=00:40:00 -o ${FULL_LOG_BASE}/m0m1j0_full_${i}_retry.out -e ${FULL_LOG_BASE}/m0m1j0_full_${i}_retry.err studies/m0m1j0_cms/cluster/pbs_m0m1j0_full.sh"
        done
    fi
    if [[ $n_unknown -gt 0 ]]; then
        echo "$n_unknown index(es) have no qstat record at all (never submitted, or purged from scheduler history) -- check manually."
    fi
fi
