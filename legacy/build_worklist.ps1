<#
.SYNOPSIS
  Builds worklist.json - the deduped, capped list of offers the Cowork orchestrator will apply to.

.DESCRIPTION
  Everything deterministic happens here, in code; nothing deterministic happens in the chat.
  An LLM reading applications_log.jsonl into context just to compare URLs burns tokens and can
  miscompare. A set lookup cannot. So this script owns the three mechanical filters:

    1. status      - only offers with status 'pending'
    2. dedup       - drop any offer whose URL already appears in applications_log.jsonl
                     (any outcome; the log is the anti-double-apply record, ARCHITECTURE.md 3.1)
    3. volume      - -Limit caps this run (default 10)

  Because dedup already removes everything in the log, consecutive runs walk forward through the
  queue: each run hands over the *next* -Limit offers, never the ones already applied to.

  Output: src\worklist.json, an array the orchestrator consumes verbatim and never re-filters.

  Layout note: this script lives in the project root and reads offers_queue.json from there,
  but writes into src\ - the only folder Cowork mounts. offers_queue.json therefore stays
  outside the agent's filesystem entirely, which is why the orchestrator prompt no longer has
  to forbid reading it.

.PARAMETER Limit
  Max offers to emit for this run. Default 10. Use 0 for the entire remaining queue.

.PARAMETER OutFile
  Where to write the worklist. Default src\worklist.json.

.PARAMETER DryRun
  Print the worklist to the console; write nothing.

.EXAMPLE
  # The next 10 unapplied offers
  .\build_worklist.ps1

.EXAMPLE
  # Careful run: a single offer
  .\build_worklist.ps1 -Limit 1

.EXAMPLE
  # See what would be selected, write nothing
  .\build_worklist.ps1 -DryRun
#>

[CmdletBinding()]
param(
    [int]    $Limit   = 10,
    [string] $OutFile = 'src\worklist.json',
    [switch] $DryRun
)

$ErrorActionPreference = 'Stop'
$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

$SrcDir    = Join-Path $ProjectDir 'src'
$QueueFile = Join-Path $ProjectDir 'offers_queue.json'
$LogFile   = Join-Path $SrcDir     'applications_log.jsonl'
if (-not (Test-Path $QueueFile)) { throw "Missing required file: offers_queue.json" }
if (-not (Test-Path $SrcDir))    { throw "Missing required folder: src\ (the folder Cowork mounts)" }
if (-not [System.IO.Path]::IsPathRooted($OutFile)) { $OutFile = Join-Path $ProjectDir $OutFile }

# --- load queue --------------------------------------------------------------
# -Encoding UTF8 is mandatory: PS 5.1's Get-Content defaults to the ANSI codepage and would
# turn "Jelenia Gora"'s accented chars into mojibake, which then flows into the application.
$offers = Get-Content $QueueFile -Raw -Encoding UTF8 | ConvertFrom-Json
if ($null -eq $offers) { Write-Host 'Queue is empty. Nothing to do.' -ForegroundColor Yellow; return }
if ($offers -isnot [System.Array]) { $offers = @($offers) }

# --- read the log once: every URL ever applied to -----------------------------
# An unparsable line is a hole in the anti-double-apply record, so it is fatal rather than a
# warning: continuing would silently re-apply to whatever offer that line was hiding.
$appliedUrls = New-Object System.Collections.Generic.HashSet[string]

if (Test-Path $LogFile) {
    $n = 0
    foreach ($line in Get-Content $LogFile -Encoding UTF8) {
        $n++
        $t = $line.Trim()
        if ($t.Length -eq 0) { continue }
        try { $obj = $t | ConvertFrom-Json } catch { throw "applications_log.jsonl line ${n} is not valid JSON. Repair it before running; a line that will not parse is an application this script cannot see, and it would be applied to twice." }
        if ($obj.url) { [void]$appliedUrls.Add([string]$obj.url) }
    }
}

# --- filter: pending, not already applied ------------------------------------
$candidates = @()
foreach ($o in $offers) {
    if ($o.status -and $o.status -ne 'pending') { continue }
    if ($appliedUrls.Contains([string]$o.url)) {
        Write-Host "SKIP (already in log): $($o.company) - $($o.title)" -ForegroundColor DarkGray
        continue
    }
    $candidates += $o
}

# --- apply the volume cap ----------------------------------------------------
$worklist = @()
if ($candidates.Count -gt 0) {
    $take = if ($Limit -gt 0) { [Math]::Min($Limit, $candidates.Count) } else { $candidates.Count }
    $worklist = @($candidates[0..($take - 1)])
}

if ($worklist.Count -eq 0) {
    Write-Host ""
    Write-Host 'No pending offers to apply to.' -ForegroundColor Yellow
    return
}

# --- report ------------------------------------------------------------------
Write-Host ""
Write-Host "Worklist - $($worklist.Count) offer(s)" -ForegroundColor Cyan
Write-Host "  already applied : $($appliedUrls.Count) in log" -ForegroundColor DarkGray
Write-Host "  candidates      : $($candidates.Count) pending & unapplied" -ForegroundColor DarkGray
Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan
$n = 0
foreach ($o in $worklist) {
    $n++
    Write-Host "[$n] $($o.company) - $($o.title)" -ForegroundColor Green
    Write-Host "    $($o.url)" -ForegroundColor DarkGray
}
Write-Host ""

if ($DryRun) {
    Write-Host "[DryRun] would write: $OutFile" -ForegroundColor Yellow
    return
}

# ConvertTo-Json collapses a 1-element array into a bare object in PS 5.1; force array shape
# so the orchestrator always parses a list.
$json = $worklist | ConvertTo-Json -Depth 6
if ($worklist.Count -eq 1) { $json = "[$json]" }

# Out-File -Encoding utf8 emits a BOM in PS 5.1, which trips strict JSON parsers. Write UTF-8
# without one.
[System.IO.File]::WriteAllText($OutFile, $json, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "Wrote $OutFile" -ForegroundColor Cyan
Write-Host "Next: open the Claude desktop app (Cowork), connect the src\ folder (NOT this one)," -ForegroundColor DarkGray
Write-Host "and give it orchestrator_instructions.md as the task." -ForegroundColor DarkGray
