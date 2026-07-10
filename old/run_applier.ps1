<#
.SYNOPSIS
  DEPRECATED - superseded by build_worklist.ps1 + the Cowork orchestrator. Do not run.

.DESCRIPTION
  DEPRECATED (2026-07-09). This script launches `claude -p`, i.e. the standalone Claude Code
  CLI, whose claude-in-chrome server forwards raw file *paths* to the Chrome extension. The
  extension now rejects those and requires base64 bytes, so **the CV silently fails to attach**
  and every application goes out without one. See CLAUDE_DESKTOP_AND_COWORK.md sec 3.

  Use instead (CLAUDE.md "Running it", ARCHITECTURE.md sec 5C):
    1. .\build_worklist.ps1            -> writes worklist.json (dedup, -Limit, -DailyCap)
    2. Claude desktop app (Cowork), connect this folder, task = orchestrator_instructions.md
       -> spawns one fresh subagent per offer; CV upload works there.

  Kept only as a reference for the old per-offer session loop. Running it requires -IKnowItsBroken.

  --- original description ---
  Reads offers_queue.json, skips offers already recorded in applications_log.jsonl
  (anti-double-apply, ARCHITECTURE.md sec 3.1), and for every remaining pending offer spawns
  an independent `claude -p` session that reads applier_instructions.md + profile.md and
  drives the application in Chrome via the claude-in-chrome MCP.

  One session per offer = no context bloat, and one bad page can't poison the rest.
  Between offers it waits a human-like, jittered delay (anti-account-abuse, sec 5B).

.PARAMETER Mode
  review (default) = fill everything, stop before final Submit.
  auto             = fill and Submit. Only flip to this once review mode is proven.

.PARAMETER DelaySeconds
  Base pause between offers. A random 0.5x..1.5x jitter is applied. Default 90.

.PARAMETER Limit
  Max offers to process this run (0 = all). Useful for a careful first run: -Limit 1.

.PARAMETER Model
  Model id for the sessions. Default claude-opus-4-8.

.PARAMETER PermissionMode
  Passed to claude. Browser automation needs bypassPermissions so sessions don't hang on
  tool prompts. Change only if you have a tighter allowlist configured.

.PARAMETER DryRun
  Print what would run (offers, prompt, command) without launching any session.

.EXAMPLE
  # Careful first run: one offer, review mode
  .\run_applier.ps1 -Limit 1

.EXAMPLE
  # Whole queue, still review mode, slower pacing
  .\run_applier.ps1 -DelaySeconds 150

.EXAMPLE
  # Auto-submit the whole queue (only after review mode is proven)
  .\run_applier.ps1 -Mode auto
#>

[CmdletBinding()]
param(
    [ValidateSet('review', 'auto')] [string] $Mode = 'review',
    [int]    $DelaySeconds   = 90,
    [int]    $Limit          = 0,
    [string] $Model          = 'claude-opus-4-8',
    [string] $PermissionMode = 'bypassPermissions',
    [switch] $DryRun,
    [switch] $IKnowItsBroken
)

$ErrorActionPreference = 'Stop'
$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

# --- deprecation guard -------------------------------------------------------
# This path cannot attach a CV (see the header). Failing loudly here beats sending a dozen
# CV-less applications and discovering it in applications_log.jsonl afterwards.
if (-not $IKnowItsBroken) {
    Write-Host ""
    Write-Host "run_applier.ps1 is DEPRECATED and will apply WITHOUT a CV." -ForegroundColor Red
    Write-Host "  The Claude Code CLI's file_upload forwards raw paths; the Chrome extension" -ForegroundColor DarkGray
    Write-Host "  rejects them. Only Cowork (desktop app) can attach the CV." -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Use instead:" -ForegroundColor Cyan
    Write-Host "  1. .\build_worklist.ps1" -ForegroundColor Cyan
    Write-Host "  2. Claude desktop app (Cowork) -> connect this folder -> task = orchestrator_instructions.md" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To run it anyway (it will not attach a CV): -IKnowItsBroken" -ForegroundColor DarkGray
    Write-Host ""
    return
}
Write-Warning "run_applier.ps1: running the DEPRECATED CLI path. The CV will NOT be attached."

$QueueFile = Join-Path $ProjectDir 'offers_queue.json'
$LogFile   = Join-Path $ProjectDir 'applications_log.jsonl'
$LogsDir   = Join-Path $ProjectDir 'logs'
if (-not (Test-Path $LogsDir)) { New-Item -ItemType Directory -Path $LogsDir | Out-Null }

# --- sanity checks -----------------------------------------------------------
$claude = Get-Command claude -ErrorAction SilentlyContinue
if ($null -eq $claude) {
    throw "The 'claude' CLI was not found on PATH. Install Claude Code and ensure 'claude' is runnable."
}
foreach ($f in @('applier_instructions.md', 'profile.md', 'offers_queue.json')) {
    if (-not (Test-Path (Join-Path $ProjectDir $f))) { throw "Missing required file: $f" }
}

# --- load queue --------------------------------------------------------------
$offers = Get-Content $QueueFile -Raw | ConvertFrom-Json
if ($null -eq $offers) { Write-Host 'Queue is empty. Nothing to do.'; return }
if ($offers -isnot [System.Array]) { $offers = @($offers) }

# --- dedup: URLs already in the log (any outcome) ----------------------------
$appliedUrls = New-Object System.Collections.Generic.HashSet[string]
if (Test-Path $LogFile) {
    foreach ($line in Get-Content $LogFile) {
        $t = $line.Trim()
        if ($t.Length -eq 0) { continue }
        try {
            $obj = $t | ConvertFrom-Json
            if ($obj.url) { [void]$appliedUrls.Add([string]$obj.url) }
        } catch {
            Write-Warning "Skipping unparsable log line: $t"
        }
    }
}

# --- build the worklist ------------------------------------------------------
$worklist = @()
foreach ($o in $offers) {
    if ($o.status -and $o.status -ne 'pending') { continue }   # only pending
    if ($appliedUrls.Contains([string]$o.url)) {
        Write-Host "SKIP (already in log): $($o.company) - $($o.title)" -ForegroundColor DarkGray
        continue
    }
    $worklist += $o
}
if ($Limit -gt 0 -and $worklist.Count -gt $Limit) {
    $worklist = $worklist[0..($Limit - 1)]
}

if ($worklist.Count -eq 0) { Write-Host 'No pending offers to apply to.' -ForegroundColor Yellow; return }

Write-Host ""
Write-Host "Applier - mode=$Mode  offers=$($worklist.Count)  model=$Model" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan

# --- per-offer prompt builder ------------------------------------------------
function New-OfferPrompt {
    param($Offer, [string]$RunMode)
    $offerJson = ($Offer | ConvertTo-Json -Compress)
    return @"
You are the Applier. Apply to ONE job offer for Yan Lukashevich by driving his logged-in
Chrome via the claude-in-chrome MCP tools.

Read and follow these two files in the current directory, exactly:
  - applier_instructions.md  (your operating manual: behavior, rules, the loop, logging)
  - profile.md               (the sole source of truth for facts)

Run mode: $RunMode   (review = fill, then STOP before Submit; auto = fill, then Submit)

The one offer to handle:
$offerJson

Follow the playbook end to end, including appending the outcome to applications_log.jsonl
(and todo_manual.md if blocked). Then give a short summary.
"@
}

# --- run loop ----------------------------------------------------------------
$i = 0
foreach ($offer in $worklist) {
    $i++
    $stamp   = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
    $slug    = ($offer.company -replace '[^\w]', '_')
    $runLog  = Join-Path $LogsDir "$stamp`_$slug.log"
    $prompt  = New-OfferPrompt -Offer $offer -RunMode $Mode

    Write-Host ""
    Write-Host "[$i/$($worklist.Count)] $($offer.company) - $($offer.title)" -ForegroundColor Green
    Write-Host "    $($offer.url)" -ForegroundColor DarkGray
    Write-Host "    transcript: $runLog" -ForegroundColor DarkGray

    if ($DryRun) {
        Write-Host "    [DryRun] would run: claude -p (prompt) --model $Model --permission-mode $PermissionMode --add-dir `"$ProjectDir`"" -ForegroundColor Yellow
        Write-Host "    ---- prompt ----`n$prompt`n    ----------------" -ForegroundColor DarkGray
        continue
    }

    # Fresh session per offer. --add-dir grants file access to the project dir.
    # stderr is captured by the tool harness; we tee stdout to a per-offer transcript.
    & claude -p $prompt `
        --model $Model `
        --permission-mode $PermissionMode `
        --add-dir $ProjectDir |
        Tee-Object -FilePath $runLog

    $exit = $LASTEXITCODE
    if ($exit -ne 0) {
        Write-Warning "Session for '$($offer.company)' exited with code $exit. See $runLog. Continuing."
    } else {
        Write-Host "    session finished." -ForegroundColor DarkGreen
    }

    # human-like jittered pacing between offers (skip after the last one)
    if ($i -lt $worklist.Count) {
        $jitter = Get-Random -Minimum ([int]($DelaySeconds * 0.5)) -Maximum ([int]($DelaySeconds * 1.5) + 1)
        Write-Host "    pausing $jitter s before next offer..." -ForegroundColor DarkGray
        Start-Sleep -Seconds $jitter
    }
}

Write-Host ""
Write-Host "Done. Processed $($worklist.Count) offer(s). Review applications_log.jsonl and todo_manual.md." -ForegroundColor Cyan
