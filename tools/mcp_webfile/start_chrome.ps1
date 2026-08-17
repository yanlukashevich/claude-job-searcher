<#
  Starts a SECOND Chrome, separate from your everyday one, with the DevTools port open.

      powershell -File tools\mcp_webfile\start_chrome.ps1

  Why a separate profile: Chrome refuses --remote-debugging-port on the default user-data-dir,
  so that no local program can silently drive the browser you are logged into. This profile
  starts empty -- log into justjoin/pracuj and install the Claude extension once, it persists.
#>

$Port    = 9222
$Profile = "$env:USERPROFILE\chrome-mcp"
$TestForm = Join-Path $PSScriptRoot "test_form.html"

$chrome = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe"
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $chrome) { throw "chrome.exe not found in the usual places -- edit this script." }

# Already listening? Don't start a second one on the same port.
$busy = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue
if ($busy.TcpTestSucceeded) {
    Write-Host "port $Port is already open -- reusing the running Chrome" -ForegroundColor Yellow
    return
}

Write-Host "chrome   $chrome"
Write-Host "profile  $Profile"
Write-Host "port     $Port"

& $chrome `
    "--remote-debugging-port=$Port" `
    "--user-data-dir=$Profile" `
    "--no-first-run" `
    "--no-default-browser-check" `
    $TestForm

Write-Host "`nnow run:  .venv\Scripts\python.exe tools\mcp_webfile\00_cdp_check.py"
