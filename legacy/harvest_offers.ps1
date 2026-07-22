$ErrorActionPreference = 'Stop'
$root = 'c:\Users\yanlu\prog\claude_job_seracher'
$q = 'categories=net&experienceLevels=mid&experienceLevels=junior&sortBy=publishedAt&orderBy=descending'

# --- fetch every page -------------------------------------------------------
$all = New-Object System.Collections.ArrayList
$from = 0
while ($true) {
    $r = Invoke-RestMethod -Uri "https://justjoin.it/api/candidate-api/offers?$q&from=$from&itemsCount=50" -Headers @{accept='application/json'}
    foreach ($o in $r.data) { [void]$all.Add($o) }
    $from += 50
    if ($from -ge $r.meta.totalItems) { break }
}
Write-Host "fetched raw rows: $($all.Count) (totalItems reported: $($r.meta.totalItems))"

# --- collapse per-city duplicates: same title + company = one offer ---------
$rows = New-Object System.Collections.ArrayList
$byKey = @{}
foreach ($o in $all) {
    $key = ($o.title + '@@' + $o.companyName).ToLower()
    $cities = @()
    if ($o.locations) { $cities = @($o.locations | ForEach-Object { $_.city }) }
    if (-not $cities -or $cities.Count -eq 0) { $cities = @($o.city) }

    if ($byKey.ContainsKey($key)) {
        $byKey[$key].cities += $cities          # merge extra cities into the kept row
        continue
    }
    $entry = [pscustomobject]@{
        url      = 'https://justjoin.it/job-offer/' + $o.slug
        title    = $o.title
        company  = $o.companyName
        cities   = $cities
        stack    = 'dotnet'
        status   = 'pending'
    }
    $byKey[$key] = $entry
    [void]$rows.Add($entry)
}
Write-Host "after collapsing per-city duplicates: $($rows.Count)"

# --- shape to the offers_queue.json schema ---------------------------------
$new = foreach ($e in $rows) {
    $loc = ($e.cities | Where-Object { $_ } | Select-Object -Unique) -join ' / '
    [pscustomobject]@{
        url      = $e.url
        title    = $e.title
        company  = $e.company
        location = $loc
        stack    = $e.stack
        status   = $e.status
    }
}

# --- merge with what is already in the queue (dedup by url, and title+company)
$queuePath = Join-Path $root 'offers_queue.json'
$existing = @()
if (Test-Path $queuePath) {
    # Get-Content decodes BOM-less UTF-8 as ANSI, which mangles the Polish
    # diacritics on the way back out. Read the bytes as UTF-8 explicitly.
    $raw = [System.IO.File]::ReadAllText($queuePath, (New-Object System.Text.UTF8Encoding $false))
    # PS 5.1: ConvertFrom-Json emits a JSON array as one un-enumerated object,
    # so assign first, then wrap - @(pipeline) would yield a single nested array.
    $parsed = $raw | ConvertFrom-Json
    $existing = @($parsed)
}
Write-Host "existing entries in queue: $($existing.Count)"

$seenUrl = @{}; $seenKey = @{}
$merged = New-Object System.Collections.ArrayList
foreach ($e in @($existing) + @($new)) {
    $k = ($e.title + '@@' + $e.company).ToLower()
    if ($seenUrl.ContainsKey($e.url) -or $seenKey.ContainsKey($k)) { continue }
    $seenUrl[$e.url] = $true; $seenKey[$k] = $true
    [void]$merged.Add($e)
}
Write-Host "merged total: $($merged.Count)  (added $($merged.Count - $existing.Count) new)"

# --- backup, then write -----------------------------------------------------
if (Test-Path $queuePath) { Copy-Item $queuePath "$queuePath.bak" -Force }
$json = $merged | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($queuePath, $json, (New-Object System.Text.UTF8Encoding $false))
Write-Host "wrote $queuePath"
