param(
  [switch]$StartDatabase,
  [string]$DatabaseUrl
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($DatabaseUrl) {
  $env:DATABASE_URL = $DatabaseUrl.Trim()
}

if ($StartDatabase) {
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker was requested with -StartDatabase but docker is not installed or not on PATH. Omit -StartDatabase and provide -DatabaseUrl for an external PostgreSQL database.'
  }

  docker compose -f docker-compose.vercel.yml up -d --wait postgres
  if ($LASTEXITCODE -ne 0) {
    throw 'Failed to start the local PostgreSQL container.'
  }

  if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = 'postgresql://qport:qport@127.0.0.1:5432/qport'
  }
}

if (-not $env:DATABASE_URL) {
  throw @'
DATABASE_URL is required.

Windows without Docker:
  .\scripts\dev-vercel.ps1 -DatabaseUrl "postgresql://USER:PASSWORD@HOST/DB?sslmode=require"

Or set it in the current PowerShell session first:
  $env:DATABASE_URL="postgresql://USER:PASSWORD@HOST/DB?sslmode=require"
  .\scripts\dev-vercel.ps1

Docker remains optional:
  .\scripts\dev-vercel.ps1 -StartDatabase
'@
}

if (-not $env:QPORT_COOKIE_SECURE) {
  $env:QPORT_COOKIE_SECURE = '0'
}
if (-not $env:CRON_SECRET) {
  $env:CRON_SECRET = 'qport-local-dev-only'
}

Write-Host 'QPort Vercel local runtime'
Write-Host '  Web: http://localhost:3000'
Write-Host '  API: http://localhost:8000/api/health'
Write-Host '  Database: external/local PostgreSQL via DATABASE_URL'
Write-Host '  Docker: optional (only with -StartDatabase)'

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
