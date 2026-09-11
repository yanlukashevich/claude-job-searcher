<#
Registers the nightly applier with Windows Task Scheduler, then leaves. Run once:

    powershell -ExecutionPolicy Bypass -File runner\register_nightly.ps1 [-Count 10]

At 23:00 every day it runs runner\nightly.ps1, which takes -Count offers off the queue and
applies to them in --mode auto -- they are really submitted. Roll it in gently: register with
-Count 3 for the first week and read runner\data\nightly.log in the morning, because three
unattended submissions is a cheap way to find out whether the autoclick and the Chrome
preflight hold up overnight.

    -Unregister   remove the task
    -Now          run it once immediately after registering
    -Count N      offers per night (default 10)

Two constraints, both worth knowing rather than fighting:

  * The machine must be AWAKE and LOGGED ON at 23:00. The task runs in your session, which is
    why Windows never has to store your password. StartWhenAvailable catches up a run missed
    to sleep -- the following morning, which for --mode auto is fine.
  * Chrome must be reachable. run_batch.py brings the chrome-mcp profile up itself when CDP
    9222 is silent, so this needs no help, but a Chrome already running WITHOUT the debug port
    will fail the whole batch.

This is the only scheduled task the project has; the hourly worklist picker was deleted.
#>
param(
  [switch]$Unregister,
  [switch]$Now,
  [int]$Count = 10
)

$ErrorActionPreference = "Stop"
$TaskName = "JobSeracher-NightlyApplier"

if ($Unregister) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  Write-Host "removed: $TaskName"
  return
}

$runner = Split-Path -Parent $MyInvocation.MyCommand.Path
$root   = Split-Path -Parent $runner
$script = Join-Path $runner "nightly.ps1"

$trigger = New-ScheduledTaskTrigger -Daily -At 23:00

# 4 hours is sized off real runs (222s / 335s / 615s per offer in run_log.jsonl) against the
# 900s per-offer timeout run_batch.py already enforces: ten offers cannot exceed ~2.5h, so the
# limit only ever fires on something genuinely wedged.
# IgnoreNew: a batch still running at 23:00 the next day keeps going; two appliers would fight
# over the same Chrome tab.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
              -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 4) `
              -MultipleInstances IgnoreNew

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`" -Count $Count" `
            -WorkingDirectory $root

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
  -Settings $settings `
  -Description "Applies to $Count queued offers a night (--mode auto), draining runner/data/worklist.json." `
  -Force | Out-Null

Write-Host "registered: $TaskName"
Write-Host "  runs   : powershell -File `"$script`" -Count $Count"
Write-Host "  when   : 23:00 daily"
Write-Host "  next   : $((Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime)"
Write-Host "  log    : runner\data\nightly.log"

if ($Now) {
  Start-ScheduledTask -TaskName $TaskName
  Write-Host "started once now - watch runner\data\nightly.log"
}
