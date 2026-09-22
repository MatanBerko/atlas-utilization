#!/bin/bash
# ---------------------------------------------------------------------------
# status_pilot.sh
#
# Summarizes the m0m1j0 CMS pilot's 4-job array, reading the job id from
# submitted_jobs.txt (written by submit_pilot.sh). Mirrors
# studies/hgg_cms/cluster/status_full.sh's own qstat-parsing approach
# (bulk `qstat -xft "<array-id>[]..."` call, awk-parsed) and its fix for
# PBS Pro already appending "[]" to an array jobid itself.
#
# Login shells on this cluster are zsh, where an unquoted "[...]" in a job
# id is glob-expanded -- every qstat/job-id argument here is double-quoted
# for exactly that reason.
#
# For each finished subjob, also checks that its expected output
# (job_metadata.json + all_histograms.root under job_<i>/) actually
# exists -- an exit code of 0 with no such output is flagged FAILED.
#
# QSTAT_CMD can be overridden (default: "qstat") for testing against a
# mocked qstat script.
# ---------------------------------------------------------------------------
set -euo pipefail

PILOT_OUTPUT_BASE="${PILOT_OUTPUT_BASE:-/storage/agrp/berkom/atlas-utilization/output/m0m1j0_pilot}"
PILOT_LOG_BASE="${PILOT_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/m0m1j0_pilot}"
JOBLIST_FILE="${JOBLIST_FILE:-${PILOT_LOG_BASE}/submitted_jobs.txt}"
QSTAT_CMD="${QSTAT_CMD:-qstat}"

if [[ ! -f "$JOBLIST_FILE" ]]; then
    echo "No job list found at $JOBLIST_FILE -- has submit_pilot.sh been run?" >&2
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
    if [[ -f "${job_dir}/job_metadata.json" ]] && [[ -f "${job_dir}/all_histograms.root" ]]; then
        echo "OK"
    else
        echo "MISSING"
    fi
}

declare -A INDEX_TO_LABEL=(
    [1]="record 30522 file 0" [2]="record 30522 file 1"
    [3]="record 30555 file 0" [4]="record 30555 file 1"
)

FAILED_INDICES=()

echo "=== m0m1j0 pilot array ==="
JOBID=$(awk '$1=="m0m1j0_pilot"{print $2}' "$JOBLIST_FILE" | tail -1)
if [[ -z "$JOBID" ]]; then
    echo "  (no m0m1j0_pilot entry in $JOBLIST_FILE)"
    exit 1
fi

QUERY_ID=$(array_query_id "$JOBID")
echo "  querying: nice $QSTAT_CMD -xft \"$QUERY_ID\""
DUMP=$(nice "$QSTAT_CMD" -xft "$QUERY_ID" 2>/dev/null || true)
PARSED=$(echo "$DUMP" | parse_array_dump)

n_queued=0; n_running=0; n_ok=0; n_failed=0; n_unknown=0
declare -A SEEN_INDEX=()
while read -r idx state exit_status walltime mem; do
    [[ -z "$idx" ]] && continue
    SEEN_INDEX["$idx"]=1
    job_dir="${PILOT_OUTPUT_BASE}/job_${idx}"
    label="${INDEX_TO_LABEL[$idx]:-unknown index}"
    case "$state" in
        Q) n_queued=$((n_queued+1)); echo "  index $idx ($label): QUEUED" ;;
        R) n_running=$((n_running+1)); echo "  index $idx ($label): RUNNING" ;;
        F)
            if [[ "$exit_status" == "0" ]] && [[ "$(check_output_exists "$job_dir")" == "OK" ]]; then
                n_ok=$((n_ok+1))
                echo "  index $idx ($label): FINISHED_OK (wall=$walltime mem=$mem)"
            else
                n_failed=$((n_failed+1))
                FAILED_INDICES+=("$idx")
                echo "  index $idx ($label): FAILED (state=$state exit_status=$exit_status wall=$walltime mem=$mem output=$(check_output_exists "$job_dir"))"
            fi
            ;;
        *) n_unknown=$((n_unknown+1)); echo "  index $idx ($label): UNKNOWN (state=$state)" ;;
    esac
done <<< "$PARSED"

for i in 1 2 3 4; do
    if [[ -z "${SEEN_INDEX[$i]:-}" ]]; then
        n_unknown=$((n_unknown+1))
        echo "  index $i (${INDEX_TO_LABEL[$i]}): UNKNOWN (no qstat record found)"
    fi
done

echo ""
echo "jobid=$JOBID: queued=$n_queued running=$n_running finished_ok=$n_ok failed=$n_failed unknown=$n_unknown (of 4)"

echo ""
echo "--- exact file URL read per job (from each job's own job_metadata.json) ---"
for i in 1 2 3 4; do
    meta="${PILOT_OUTPUT_BASE}/job_${i}/job_metadata.json"
    if [[ -f "$meta" ]]; then
        url=$(python -c "import json; print(json.load(open('$meta'))['file_url'])" 2>/dev/null || echo "ERROR reading $meta")
        n_read=$(python -c "import json; print(json.load(open('$meta'))['cutflow']['n_read'])" 2>/dev/null || echo "?")
        echo "  job_${i} (${INDEX_TO_LABEL[$i]}): $url ($n_read events read)"
    else
        echo "  job_${i} (${INDEX_TO_LABEL[$i]}): (no job_metadata.json yet)"
    fi
done

echo ""
echo "=== Summary ==="
if [[ ${#FAILED_INDICES[@]} -eq 0 ]]; then
    echo "No failures detected (among jobs currently in a finished state)."
else
    echo "Failed indices: ${FAILED_INDICES[*]}"
    echo ""
    echo "--- Retry commands (only the missing indices, per this task's own retry rule) ---"
    TS='$(date +%Y%m%d_%H%M%S)'
    for i in "${FAILED_INDICES[@]}"; do
        echo "TS=$TS; mv ${PILOT_OUTPUT_BASE}/job_${i} ${PILOT_OUTPUT_BASE}/job_${i}_failed1_\${TS} 2>/dev/null"
        echo "qsub -J ${i}-${i} -v OUTPUT_BASE=${PILOT_OUTPUT_BASE},REPO_DIR=\$REPO_DIR -o ${PILOT_LOG_BASE}/m0m1j0_pilot_${i}_retry.out -e ${PILOT_LOG_BASE}/m0m1j0_pilot_${i}_retry.err studies/m0m1j0_cms/cluster/pbs_m0m1j0_pilot.sh"
        echo "# fallback if -J ${i}-${i} is rejected:"
        echo "# qsub -v PBS_ARRAY_INDEX=${i},OUTPUT_BASE=${PILOT_OUTPUT_BASE},REPO_DIR=\$REPO_DIR -o ${PILOT_LOG_BASE}/m0m1j0_pilot_${i}_retry.out -e ${PILOT_LOG_BASE}/m0m1j0_pilot_${i}_retry.err studies/m0m1j0_cms/cluster/pbs_m0m1j0_pilot.sh"
    done
fi
