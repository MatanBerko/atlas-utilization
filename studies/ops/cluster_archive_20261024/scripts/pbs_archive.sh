#!/bin/bash
# Cluster archive, Phase 2: one approved folder per array subjob (0-based line
# of $LIST). Manifest -> tar.gz -> verify. The original is NOT removed.
#
#   ROOT = /storage/agrp/berkom/atlas-utilization
#   NAME = the folder path with "/" replaced by "_"
#   $ARCH/<NAME>.manifest.tsv, $ARCH/<NAME>.tar.gz; the verification result
#   goes to $REPORT_DIR/verify/<NAME>.verify.json
# An existing archive, manifest or verify file is never overwritten: the job
# STOPs. Files are written under a ".partial" name and renamed only when done.
#PBS -q N
#PBS -m n
#PBS -S /bin/bash
set -euo pipefail

ROOT=/storage/agrp/berkom/atlas-utilization
ARCH="$ROOT/archive/20261024"
R="${REPORT_DIR:?}"
LIST="${LIST:?}"
PY=/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline/bin/python
export HOME="${TMPDIR:-/tmp}/arch_home"; mkdir -p "$HOME"
export PYTHONDONTWRITEBYTECODE=1

IDX="${PBS_ARRAY_INDEX:?}"
REL=$(sed -n "$((IDX + 1))p" "$LIST")
[[ -n "$REL" && "$REL" != /* && "$REL" != *..* ]] || { echo "bad list line $IDX: '$REL'" >&2; exit 1; }
NAME="${REL//\//_}"
echo "idx=$IDX rel=$REL name=$NAME host=$(hostname) start=$(date)"
for f in "$ARCH/$NAME.manifest.tsv" "$ARCH/$NAME.tar.gz" "$R/verify/$NAME.verify.json" \
         "$ARCH/$NAME.manifest.tsv.partial" "$ARCH/$NAME.tar.gz.partial"; do
    [[ -e "$f" ]] && { echo "STOP: $f already exists" >&2; exit 1; }
done
[[ -d "$ROOT/$REL" && ! -L "$ROOT/$REL" ]] || { echo "STOP: $ROOT/$REL is not a folder" >&2; exit 1; }

# a. manifest from disk
$PY -u "$R/archive_tool.py" manifest --root "$ROOT" --rel "$REL" --out "$ARCH/$NAME.manifest.tsv.partial"
mv -n "$ARCH/$NAME.manifest.tsv.partial" "$ARCH/$NAME.manifest.tsv"
echo "manifest done $(date)"

# b. archive, relative paths (REL/...), timestamps kept (GNU tar default)
tar -C "$ROOT" -czf "$ARCH/$NAME.tar.gz.partial" "$REL"
mv -n "$ARCH/$NAME.tar.gz.partial" "$ARCH/$NAME.tar.gz"
ls -l "$ARCH/$NAME.tar.gz"
echo "tar done $(date)"

# c. verify: gzip -t, member list == manifest, every sha256 from the stream
$PY -u "$R/archive_tool.py" verify --manifest "$ARCH/$NAME.manifest.tsv" \
    --archive "$ARCH/$NAME.tar.gz" --out "$R/verify/$NAME.verify.json"
echo "verify done $(date)"
