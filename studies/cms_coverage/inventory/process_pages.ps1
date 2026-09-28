# Not part of the inventory's evidence -- a one-off local processing helper
# used to strip the portal API's internal `_file_indices` field (a huge,
# purely-internal per-file checksum manifest, irrelevant to this inventory
# -- record/file/event/size totals come from `distribution`, not this) from
# fetched search-result pages before committing them as evidence, and to
# build the flat summary rows this task's machine-readable table needs.
param(
    [string]$InputDir,
    [string]$OutputDir,
    [string]$Prefix,
    [int]$NumPages,
    [string]$RowsOutCsv
)

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$rows = @()

for ($page = 1; $page -le $NumPages; $page++) {
    $inFile = Join-Path $InputDir "${Prefix}_page_${page}.json"
    if (-not (Test-Path $inFile)) { Write-Host "MISSING: $inFile"; continue }
    $p = Get-Content -Raw $inFile | ConvertFrom-Json

    foreach ($h in $p.hits.hits) {
        if ($h.metadata.PSObject.Properties.Name -contains "_file_indices") {
            $h.metadata.PSObject.Properties.Remove("_file_indices")
        }
    }

    # Keep aggregations only on page 1 (identical/redundant on every page).
    if ($page -gt 1) {
        $p.PSObject.Properties.Remove("aggregations")
    }

    $outFile = Join-Path $OutputDir "${Prefix}_page_${page}.json"
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
            collision_energy = $m.collision_information.energy
            collision_type  = $m.collision_information.type
            date_created    = $m.date_created
            cmssw_release   = $m.system_details.release
            global_tag      = $m.system_details.global_tag
            doi             = $m.doi
        }
    }
    Write-Host "processed page $page : $($p.hits.hits.Count) hits"
}

$rows | Export-Csv -Path $RowsOutCsv -NoTypeInformation -Encoding UTF8
Write-Host "wrote $($rows.Count) rows to $RowsOutCsv"
