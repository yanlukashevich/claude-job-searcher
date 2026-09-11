<#
The nightly applier run. This is what the scheduled task actually launches -- never
run_batch.py directly, because nobody is at the keyboard at 23:00 and stdout would go nowhere.

    powershell -File runner\nightly.ps1 [-Count 10] [-Mode auto]

It appends a dated block to runner\data\nightly.log and records the exit code, so a morning
`Get-Content runner\data\nightly.log -Tail 40` answers all three questions at once: did it run,
what did it do, and how did it end.

Exit codes, passed straight through from run_batch.py:
    0   the batch finished
    1   nothing to do, or something is misconfigured (an empty queue lands here)
    2   the batch STOPPED against the Claude usage limit. The offers it never reached are
        still queued and unlogged; tonight cost a batch, not a queue.

An empty queue exits early rather than launching Chrome for nothing.
#>
param(
  [int]$Count = 10,
  [ValidateSet("review","auto")][string]$Mode = "auto"
)

$ErrorActionPreference = "Continue"

$runner = Split-Path -Parent $MyInvocation.MyCommand.Path
$root   = Split-Path -Parent $runner
$log      = Join-Path $runner "data\nightly.log"
$worklist = Join-Path $runner "data\worklist.json"

Set-Location $root

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $log -Encoding utf8 -Value @"

================================================================================
$stamp  nightly applier  -Count $Count -Mode $Mode
"@

# The queue is hand-picked and can simply be empty; that is a quiet night, not a failure.
$queued = 0
if (Test-Path $worklist) {
  try { $queued = @(Get-Content $worklist -Raw | ConvertFrom-Json).Count } catch { $queued = 0 }
}
if ($queued -eq 0) {
  Add-Content -Path $log -Encoding utf8 -Value "queue empty - nothing to do, exiting."
  exit 0
}
Add-Content -Path $log -Encoding utf8 -Value "queue: $queued offer(s), taking up to $Count"

# *>> captures stdout AND stderr; run_batch.py prints its whole summary on stdout.
python runner\run_batch.py --mode $Mode --limit $Count *>> $log
$code = $LASTEXITCODE

$done = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$note = switch ($code) {
  0 { "finished" }
  2 { "STOPPED on the usage limit - the offers not reached are still queued" }
  default { "failed" }
}
Add-Content -Path $log -Encoding utf8 -Value "$done  exit $code - $note"
exit $code
