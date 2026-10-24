#!/bin/bash
# Cluster archive, Phase 3: remove the originals Matan named in
# "delete originals: ..." (24 Oct 2026) = $LIST, one folder at a time,
# stopping at the first failed check. For each folder, just before deleting:
#   1. the Phase 2 verify file says "verified": true;
#   2. gzip -t on its archive;
#   3. the archive's member count (tar -tzf) == the manifest's line count;
#   4. the folder's entry count on disk now == the manifest's line count
#      (the folder has not changed since it was archived);
# then `rm -rf -- "$ROOT/$REL"` on that exact path (no wildcard) and a check
# that it is gone. One line per folder goes to $REPORT_DIR/delete_log.tsv.
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
set -euo pipefail

ROOT=/storage/agrp/berkom/atlas-utilization
ARCH="$ROOT/archive/20261024"
R="${REPORT_DIR:?}"
LIST="${LIST:?}"
LOG="$R/delete_log.tsv"
export HOME="${TMPDIR:-/tmp}/del_home"; mkdir -p "$HOME"

echo "start $(date) on $(hostname)"
(lfs quota -u berkom /storage | tail -1 | sed 's/^/quota before: /') || true
[[ -e "$LOG" ]] && { echo "STOP: $LOG exists" >&2; exit 1; }
printf "folder\tmanifest_entries\tarchive_members\tdisk_entries_before\tdeleted\ttime\n" > "$LOG"

while read -r REL; do
    [[ -z "$REL" ]] && continue
    # only plain relative paths under logs/ or work/, no "..", no wildcard characters
    [[ "$REL" =~ ^(logs|work/[A-Za-z0-9_]+)$ ]] || { echo "STOP: refusing path '$REL'" >&2; exit 1; }
    NAME="${REL//\//_}"
    T="$ROOT/$REL"
    [[ -d "$T" && ! -L "$T" ]] || { echo "STOP: $T is not a real folder" >&2; exit 1; }
    grep -q '"verified": true' "$R/verify/$NAME.verify.json" || { echo "STOP: $NAME not verified in Phase 2" >&2; exit 1; }
    gzip -t "$ARCH/$NAME.tar.gz" || { echo "STOP: gzip test failed for $NAME" >&2; exit 1; }
    n_man=$(wc -l < "$ARCH/$NAME.manifest.tsv")
    n_arc=$(tar -tzf "$ARCH/$NAME.tar.gz" | wc -l)
    n_disk=$(find "$T" | wc -l)
    echo "$REL: manifest=$n_man archive=$n_arc disk=$n_disk"
    [[ "$n_man" -eq "$n_arc" && "$n_man" -eq "$n_disk" ]] || { echo "STOP: counts differ for $REL" >&2; exit 1; }
    rm -rf -- "$T"
    [[ ! -e "$T" ]] || { echo "STOP: $T still exists after rm" >&2; exit 1; }
    printf "%s\t%s\t%s\t%s\tyes\t%s\n" "$REL" "$n_man" "$n_arc" "$n_disk" "$(date '+%F %T')" >> "$LOG"
done < "$LIST"

(lfs quota -u berkom /storage | tail -1 | sed 's/^/quota after: /') || true
echo "done $(date)"
