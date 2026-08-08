<#
Registers the hourly worklist refresh with Windows Task Scheduler, then leaves. Run once:

    powershell -ExecutionPolicy Bypass -File finder\register_auto_worklist.ps1

The task fires at :40 of every hour -- 20 minutes before the full hour, so a fresh five are
waiting by the time you start Cowork on the hour. It runs pythonw.exe, so no console window
pops up 24 times a day; that is also why auto_worklist.py keeps its own run log
(finder/data/auto_worklist_log.jsonl) -- nothing is watching stdout.

    -Unregister   remove the task
    -Now          run it once immediately after registering (overwrites src/worklist.json)

Runs only while you are logged on, which is when the machine is on anyway, and means Windows
never has to store your password. StartWhenAvailable catches up a run missed to sleep.
#>
param(
  [switch]$Unregister,
  [switch]$Now
)

$ErrorActionPreference = "Stop"
$TaskName = "JobSeracher-AutoWorklist"

if ($Unregister) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  Write-Host "removed: $TaskName"
  return
}

$finder = Split-Path -Parent $MyInvocation.MyCommand.Path
$root   = Split-Path -Parent $finder
$script = Join-Path $finder "auto_worklist.py"

# pythonw runs it windowless; fall back to python.exe if this install lacks it.
$py = (Get-Command python).Source
$pyw = Join-Path (Split-Path -Parent $py) "pythonw.exe"
if (Test-Path $pyw) { $py = $pyw }

$action = New-ScheduledTaskAction -Execute $py -Argument "`"$script`"" -WorkingDirectory $root

# -Once + RepetitionInterval is the only way to say "every hour, on a minute I choose"; the
# built-in Daily/Hourly triggers align to whenever you registered them.
$at = (Get-Date -Minute 40 -Second 0 -Millisecond 0).AddHours(-1)
$trigger = New-ScheduledTaskTrigger -Once -At $at `
             -RepetitionInterval (New-TimeSpan -Hours 1) `
             -RepetitionDuration (New-TimeSpan -Days 1)
# "repeat forever" is an ABSENT duration in the task XML, and the cmdlet cannot produce one --
# [TimeSpan]::MaxValue serializes to P99999999D and the scheduler rejects it as out of range.
# So build a finite one and blank it out here.
$trigger.Repetition.Duration = ""
$trigger.Repetition.StopAtDurationEnd = $false

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
              -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
              -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
  -Settings $settings -Description "Writes src/worklist.json: 5 unapplied offers from lone-posting companies." `
  -Force | Out-Null

Write-Host "registered: $TaskName"
Write-Host "  runs   : $py `"$script`""
Write-Host "  when   : :40 of every hour"
Write-Host "  next   : $((Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime)"
Write-Host "  log    : finder\data\auto_worklist_log.jsonl"

if ($Now) {
  Start-ScheduledTask -TaskName $TaskName
  Write-Host "started once now"
}
