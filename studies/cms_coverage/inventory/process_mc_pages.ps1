# One-off local processing helper (see process_pages.ps1's own comment for
# why _file_indices is stripped). Generalized to an arbitrary glob of
# already-fetched page files (any naming pattern), for the MC format tiers.
#
# Also strips methodology/abstract/usage/validation/dataset_semantics_files/
# pileup/license/collections/pids/relations/title_additional -- discovered,
# not assumed: after stripping only _file_indices/files (as the collision-
# data version does), MC record pages were STILL ~1.2GB combined for
# ~28,000 records because `methodology` alone runs ~50KB/record (a long
# free-text production-methodology description, not needed for this
# inventory's numeric fields). None of these fields are used anywhere in
# this task's row extraction below or in INVENTORY.md.
param(
    [string]$InputGlob,
    [string]$OutputDir,
    [string]$RowsOutCsv
)

$dropFields = @(
    "_file_indices", "files", "methodology", "abstract", "usage",
    "validation", "dataset_semantics_files", "pileup", "license",
    "collections", "pids", "relations", "title_additional", "publisher",
    "accelerator", "collaboration", "_bucket", "_availability_details"
)

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$rows = @()
$files = Get-ChildItem $InputGlob | Sort-Object Name

foreach ($inFile in $files) {
    $p = Get-Content -Raw $inFile.FullName | ConvertFrom-Json

    foreach ($h in $p.hits.hits) {
        foreach ($f in $dropFields) {
            if ($h.metadata.PSObject.Properties.Name -contains $f) {
                $h.metadata.PSObject.Properties.Remove($f)
            }
        }
    }

    $outFile = Join-Path $OutputDir $inFile.Name
    $p | ConvertTo-Json -Depth 12 -Compress | Set-Content -Path $outFile -Encoding UTF8

    foreach ($h in $p.hits.hits) {
        $m = $h.metadata
        $rows += [PSCustomObject]@{
            recid           = $m.recid
            title           = $m.title
            type_primary    = $m.type.primary
            type_secondary  = ($m.type.secondary -join ";")
            formats         = ($m.distribution.formats -join ";")
            number_files    = $m.distribution.number_files
            number_events   = $m.distribution.number_events
            size_bytes      = $m.distribution.size
            run_period      = ($m.run_period -join ";")
            date_created    = $m.date_created
            cmssw_release   = ($m.system_details.release -join ";")
            doi             = $m.doi
        }
    }
    Write-Host "processed $($inFile.Name): $($p.hits.hits.Count) hits (running row total: $($rows.Count))"
}

$rows | Export-Csv -Path $RowsOutCsv -NoTypeInformation -Encoding UTF8
Write-Host "wrote $($rows.Count) rows to $RowsOutCsv"
