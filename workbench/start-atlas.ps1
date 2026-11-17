$ErrorActionPreference = 'Stop'
$atlasDir = $PSScriptRoot
$atlasUrl = 'http://127.0.0.1:8765/'
try {
  $atlasCheck = Invoke-RestMethod -Uri ($atlasUrl + 'api/state') -Headers @{'X-Atlas-Request'='1'} -TimeoutSec 2
  Start-Process $atlasUrl
  exit
} catch {}
$atlasPython = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $atlasPython) { throw 'Python 3.10 or newer is required. Install Python, then retry.' }
Start-Process -FilePath $atlasPython -ArgumentList @('"' + (Join-Path $atlasDir 'atlas_server.py') + '"') -WorkingDirectory $atlasDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $atlasDir 'service.log') -RedirectStandardError (Join-Path $atlasDir 'service-error.log')
for ($atlasAttempt=0; $atlasAttempt -lt 20; $atlasAttempt++) {
  Start-Sleep -Milliseconds 300
  try { $atlasCheck = Invoke-RestMethod -Uri ($atlasUrl + 'api/state') -Headers @{'X-Atlas-Request'='1'} -TimeoutSec 1; Start-Process $atlasUrl; exit } catch {}
}
throw 'Service did not start. See service-error.log.'
