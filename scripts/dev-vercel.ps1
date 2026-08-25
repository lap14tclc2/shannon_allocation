param(
  [string]$DatabaseUrl
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$DefaultLocalDatabaseUrl = 'postgresql://qport:qport@127.0.0.1:5432/qport'

if ($DatabaseUrl) {
  $env:DATABASE_URL = $DatabaseUrl.Trim()
}
elseif ([string]::IsNullOrWhiteSpace($env:DATABASE_URL) -or $env:DATABASE_URL.Trim() -eq '\') {
  $env:DATABASE_URL = $DefaultLocalDatabaseUrl
}

if (-not $env:QPORT_COOKIE_SECURE) {
  $env:QPORT_COOKIE_SECURE = '0'
}
if (-not $env:CRON_SECRET) {
  $env:CRON_SECRET = 'qport-local-dev-only'
}

$probe = @'
import os
import psycopg

conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3)
conn.close()
'@

$pythonExe = if (Test-Path "$Root\.venv\Scripts\python.exe") { "$Root\.venv\Scripts\python.exe" } else { "python" }

try {
  $probe | & $pythonExe -
  if ($LASTEXITCODE -ne 0) {
    throw 'PostgreSQL connectivity check failed.'
  }
}
catch {
  throw @"
Cannot connect to local PostgreSQL at:
  $env:DATABASE_URL

Install/start native PostgreSQL on Windows, then initialize the QPort database once with:
  psql -U postgres -f scripts/setup-postgres-native.sql

To use a different native PostgreSQL connection:
  .\scripts\dev-vercel.ps1 -DatabaseUrl "postgresql://USER:PASSWORD@HOST/DB"
"@
}

Write-Host 'QPort Vercel-compatible local runtime'
Write-Host '  Web: http://localhost:3000'
Write-Host '  API: http://localhost:8000/api/health'
Write-Host '  Database mode: native PostgreSQL'
Write-Host "  DATABASE_URL: $env:DATABASE_URL"

$api = Start-Process -FilePath $pythonExe -ArgumentList @(
  '-m', 'uvicorn', 'app.main:app', '--reload', '--host', '127.0.0.1', '--port', '8000'
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
