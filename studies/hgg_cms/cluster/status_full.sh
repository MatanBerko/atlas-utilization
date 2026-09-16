#!/bin/bash
# ---------------------------------------------------------------------------
# status_full.sh
#
# Summarizes the full H->gamma-gamma run's jobs, reading job IDs from a
# submitted_jobs.txt file (one "name jobid" pair per line -- exactly what
# submit_full.sh writes to logs/hgg_full/submitted_jobs.txt). Meant to run
# on the analysis node, under `nice`, and finish in seconds -- it only
# calls `qstat` (twice: once for the whole data array, once per signal
# job) and stats a handful of files per job, never reads or opens any
# actual ROOT/data file.
#
# BUG FIX (16 Sep 2026): the previous version queried each of the 133 data
# array subjobs INDIVIDUALLY as "${DATA_JOBID}[${i}]" -- but on this
# cluster, PBS Pro's own `qsub -J 1-133 ...` already returns the array's
# jobid WITH the array brackets already appended, e.g. "5045473[].pbs" (
# confirmed directly: `qstat -xft "5045473[].pbs"` correctly lists all 133
# finished subjobs with Exit_status = 0). Appending another "[${i}]" after
# that produced a malformed id like "5045473[].pbs[7]", which qstat could
# not resolve -- every subjob came back as job_state/exit_status empty,
# reported as "unknown" regardless of its real (finished, Exit_status=0)
# state. Fixed by querying the array ONCE, in bulk
# (`qstat -xft "<array-id-with-brackets>"`), which returns one
# "Job Id: <base>[<i>].<server>" block per subjob -- parsed below with
# awk -- instead of 133 separate (and, it turns out, broken) per-index
# calls. This is also much faster: 1 qstat call instead of 133.
#
# QSTAT_CMD can be overridden (default: "qstat") -- used by this task's
# own test to point at a mocked qstat script instead of the real one.
#
# For each finished job/subjob (job_state F, i.e. -x's historical-jobs
# view), this ALSO checks that its expected output actually exists
# (selected/job_metadata.json, at least one *.root file under selected/)
# -- an exit code of 0 with no such output is flagged FAILED, not OK,
# since a job can exit cleanly and still have produced nothing useful
# (e.g. an empty chunk list).
#
# Also prints, for every data job directory that exists, its reconstructed
# CERN input file (same method as merge_outputs.py's --mode data identity
# check: that job's OWN metadata_cache.json + its array index, via the
# real utils.batching.get_batch_slice_by_year -- NEVER job_metadata.json's
# own "input_files_processed", which is the intermediate parsed-chunk
# path, not the CERN URL) and flags any file assigned to more than one
# job index.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/atlas-utilization}"
FULL_BASE="${FULL_BASE:-/storage/agrp/berkom/atlas-utilization/output/hgg_full}"
FULL_LOG_BASE="${FULL_LOG_BASE:-/storage/agrp/berkom/atlas-utilization/logs/hgg_full}"
JOBLIST_FILE="${JOBLIST_FILE:-${FULL_LOG_BASE}/submitted_jobs.txt}"
QSTAT_CMD="${QSTAT_CMD:-qstat}"
PYTHON_CMD="${PYTHON_CMD:-python}"
TOTAL_DATA_INDICES="${TOTAL_DATA_INDICES:-133}"

if [[ ! -f "$JOBLIST_FILE" ]]; then
    echo "No job list found at $JOBLIST_FILE -- has submit_full.sh been run?" >&2
    exit 1
fi

# ---- qstat -f field extraction (tolerant of leading whitespace -- exact
# formatting can vary by site/version, so this greps for "key = value"
# rather than assuming fixed columns). ----
qstat_field() {
    # qstat_field "<qstat -f output>" "<field name>"
    echo "$1" | grep -E "^ *$2 = " | head -1 | sed -E "s/^ *$2 = //"
}

# ---- Bulk-parse a `qstat -xft "<array-id>[]..."` dump: one line per
# subjob found, "<index> <state> <exit_status> <walltime> <mem>". Any
# field qstat didn't report comes out as ".". ----
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

# ---- Build the "<base>[].<server>" query id for the whole array from
# whatever form DATA_JOBID was stored in (some sites' qsub already returns
# it WITH "[]"; be tolerant of both). ----
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
    QUERY_ID=$(array_query_id "$DATA_JOBID")
    echo "  querying: nice $QSTAT_CMD -xft \"$QUERY_ID\" (one bulk call for all $TOTAL_DATA_INDICES subjobs)"
    DUMP=$(nice "$QSTAT_CMD" -xft "$QUERY_ID" 2>/dev/null || true)
    PARSED=$(echo "$DUMP" | parse_array_dump)

    n_queued=0; n_running=0; n_ok=0; n_failed=0; n_unknown=0
    declare -A SEEN_INDEX=()
    while read -r idx state exit_status walltime mem; do
        [[ -z "$idx" ]] && continue
        SEEN_INDEX["$idx"]=1
        sel_dir="${FULL_BASE}/data/job_${idx}/selected"
        case "$state" in
            Q) n_queued=$((n_queued+1)) ;;
            R) n_running=$((n_running+1)) ;;
            F)
                if [[ "$exit_status" == "0" ]] && [[ "$(check_output_exists "$sel_dir")" == "OK" ]]; then
                    n_ok=$((n_ok+1))
                else
                    n_failed=$((n_failed+1))
                    FAILED_DATA_INDICES+=("$idx")
                    echo "  index $idx: FAILED (state=$state exit_status=$exit_status wall=$walltime mem=$mem output=$(check_output_exists "$sel_dir"))"
                fi
                ;;
            *) n_unknown=$((n_unknown+1)) ;;
        esac
    done <<< "$PARSED"

    # Any index 1..TOTAL_DATA_INDICES that qstat's dump had no block for at
    # all (e.g. never submitted, or already purged from scheduler history).
    for i in $(seq 1 "$TOTAL_DATA_INDICES"); do
        if [[ -z "${SEEN_INDEX[$i]:-}" ]]; then
            n_unknown=$((n_unknown+1))
        fi
    done

    echo "  jobid=$DATA_JOBID: queued=$n_queued running=$n_running finished_ok=$n_ok failed=$n_failed unknown=$n_unknown (of $TOTAL_DATA_INDICES)"

    echo ""
    echo "  --- reconstructed input file per data job (metadata_cache.json + batch index; flags duplicates) ---"
    FILE_LIST=$("$PYTHON_CMD" "$(dirname "$0")/merge_outputs.py" --print-data-job-files \
        --jobs-base "${FULL_BASE}/data" --total-batches "$TOTAL_DATA_INDICES" 2>&1 || true)
    if [[ -z "$FILE_LIST" ]]; then
        echo "    (no job_<i> directories found yet under ${FULL_BASE}/data)"
    else
        echo "$FILE_LIST" | while read -r idx key_or_err url_or_msg; do
            echo "    job_${idx}: ${key_or_err} -> ${url_or_msg}"
        done
        DUP_URLS=$(echo "$FILE_LIST" | awk -F'\t' '$2!="ERROR"{print $3}' | sort | uniq -d)
        if [[ -n "$DUP_URLS" ]]; then
            echo "    !!! DUPLICATE input file(s) assigned to more than one job index:"
            echo "$DUP_URLS" | while read -r dup_url; do
                jobs_with_dup=$(echo "$FILE_LIST" | awk -F'\t' -v u="$dup_url" '$3==u{print $1}' | paste -sd, -)
                echo "        $dup_url  <- jobs: $jobs_with_dup"
            done
        else
            echo "    no duplicate input files across present job directories."
        fi
    fi
fi

echo ""
echo "=== SIGNAL jobs ==="
while read -r name jobid; do
    [[ "$name" == data_array ]] && continue
    [[ -z "$name" ]] && continue
    label="${name#signal_}"
    out=$(nice "$QSTAT_CMD" -xf "$jobid" 2>/dev/null || true)
    state=$(qstat_field "$out" "job_state")
    exit_status=$(qstat_field "$out" "Exit_status")
    walltime=$(qstat_field "$out" "resources_used.walltime")
    mem=$(qstat_field "$out" "resources_used.mem")
    sel_dir="${FULL_BASE}/signal/${label}/selected"
    status="UNKNOWN"
    case "${state:-UNKNOWN}" in
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
    echo "  $label (jobid=$jobid): $status (state=${state:-UNKNOWN} exit_status=${exit_status:-.} wall=${walltime:-.} mem=${mem:-.} output=$(check_output_exists "$sel_dir"))"
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
