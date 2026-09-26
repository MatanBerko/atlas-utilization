# Combines every per-tier rows CSV already extracted (collision data,
# nanoaodsim/miniaodsim/aodsim non-SUSY, small MC tiers, Derived) into one
# master table. Supersymmetry (10,896 nanoaodsim + 11,379 miniaodsim
# records) is NOT included row-by-row -- see INVENTORY.md's methodology
# section for why (exceeds the portal API's 10,000-result deep-pagination
# window as a single category query; its counts are exact, from the API's
# own facet aggregation, but per-record title/file/event/size detail was
# not fetched for it).
$sources = @(
    @{ path = "C:\Users\matan\AppData\Local\Temp\inv_raw\data_rows_clean.csv"; usability = "DIRECTLY_USABLE_OR_WORK" },
    @{ path = "C:\Users\matan\AppData\Local\Temp\inv_raw\nano_by_cat_rows2.csv"; usability = "DIRECTLY_USABLE" },
    @{ path = "C:\Users\matan\AppData\Local\Temp\inv_raw\mini_by_cat_rows2.csv"; usability = "USABLE_WITH_WORK" },
    @{ path = "C:\Users\matan\AppData\Local\Temp\inv_raw\mc_aodsim_rows2.csv"; usability = "USABLE_WITH_WORK" },
    @{ path = "C:\Users\matan\AppData\Local\Temp\inv_raw\mc_othertiers_rows2.csv"; usability = "NOT_USABLE" },
    @{ path = "C:\Users\matan\AppData\Local\Temp\inv_raw\other_type_rows.csv"; usability = "USABLE_WITH_WORK" }
)
$all = @()
foreach ($s in $sources) {
    $rows = Import-Csv $s.path
    foreach ($r in $rows) {
        $all += [PSCustomObject]@{
            recid          = $r.recid
            title          = $r.title
            type_primary   = $r.type_primary
            type_secondary = $r.type_secondary
            formats        = $r.formats
            number_files   = $r.number_files
            number_events  = $r.number_events
            size_bytes     = $r.size_bytes
            run_period     = $r.run_period
            doi            = $r.doi
            usability_note = $s.usability
        }
    }
    Write-Host "added $($rows.Count) rows from $($s.path)"
}
Write-Host "TOTAL rows:" $all.Count
$all | Export-Csv -Path "C:\Users\matan\AppData\Local\Temp\claude\hgg_work\repo\studies\cms_coverage\inventory\master_table.csv" -NoTypeInformation -Encoding UTF8
$all | ConvertTo-Json -Depth 5 | Set-Content -Path "C:\Users\matan\AppData\Local\Temp\claude\hgg_work\repo\studies\cms_coverage\inventory\master_table.json" -Encoding UTF8
Write-Host "wrote master_table.csv and master_table.json"
