param(
  [switch]$StartDatabase
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($StartDatabase) {
  docker compose -f docker-compose.vercel.yml up -d postgres
}

if (-not $env:DATABASE_URL) {
  $env:DATABASE_URL = 'postgresql://qport:qport@127.0.0.1:5432/qport'
}
if (-not $env:QPORT_COOKIE_SECURE) {
  $env:QPORT_COOKIE_SECURE = '0'
}

Write-Host 'QPort Vercel local runtime'
Write-Host '  Web: http://localhost:3000'
Write-Host '  API: http://localhost:8000/api/health'

$api = Start-Process -FilePath 'python' -ArgumentList @(
  '-m', 'uvicorn', 'api.index:app', '--reload', '--host', '127.0.0.1', '--port', '8000'
) -PassThru -NoNewWindow

try {
  Push-Location "$Root/frontend"
  npm run dev
}
finally {
  Pop-Location
  if ($api -and -not $api.HasExited) {
    Stop-Process -Id $api.Id -Force
  }
}
