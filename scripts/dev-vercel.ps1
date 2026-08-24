param(
  [switch]$StartDatabase,
  [string]$DatabaseUrl
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$DefaultLocalDatabaseUrl = 'postgresql://qport:qport@127.0.0.1:5432/qport'

if ($DatabaseUrl) {
  $env:DATABASE_URL = $DatabaseUrl.Trim()
}

if ($StartDatabase) {
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker was requested with -StartDatabase but docker is not installed or not on PATH. Omit -StartDatabase to use native Windows PostgreSQL.'
  }

  docker compose -f docker-compose.vercel.yml up -d --wait postgres
  if ($LASTEXITCODE -ne 0) {
    throw 'Failed to start the local PostgreSQL container.'
  }

  if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = $DefaultLocalDatabaseUrl
  }
  $DatabaseMode = 'Docker PostgreSQL'
}
else {
  if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = $DefaultLocalDatabaseUrl
  }
  $DatabaseMode = 'Windows native PostgreSQL'
}

if (-not $env:QPORT_COOKIE_SECURE) {
  $env:QPORT_COOKIE_SECURE = '0'
}
if (-not $env:CRON_SECRET) {
  $env:CRON_SECRET = 'qport-local-dev-only'
}

# Fail early with a useful message instead of letting the first API request
# discover that PostgreSQL is unavailable or the qport database was not set up.
$probe = @'
import os
import psycopg

conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3)
conn.close()
'@

try {
  $probe | python -
  if ($LASTEXITCODE -ne 0) {
    throw 'PostgreSQL connectivity check failed.'
  }
}
catch {
  if ($StartDatabase) {
    throw "Cannot connect to Docker PostgreSQL at $env:DATABASE_URL. $($_.Exception.Message)"
  }
  throw @"
Cannot connect to native Windows PostgreSQL at:
  $env:DATABASE_URL

Install/start PostgreSQL, then initialize the local QPort database once with:
  psql -U postgres -f scripts/setup-postgres-native.sql

Or override the connection explicitly:
  .\scripts\dev-vercel.ps1 -DatabaseUrl "postgresql://USER:PASSWORD@HOST/DB"

Docker remains available when wanted:
  .\scripts\dev-vercel.ps1 -StartDatabase
"@
}

Write-Host 'QPort Vercel-compatible local runtime'
Write-Host '  Web: http://localhost:3000'
Write-Host '  API: http://localhost:8000/api/health'
Write-Host "  Database mode: $DatabaseMode"
Write-Host "  DATABASE_URL: $env:DATABASE_URL"

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
