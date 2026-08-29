# Safe Non-Destructive Finance Sync to Vercel/Neon
# This script ONLY syncs qport_finance catalog using transactional UPSERT.
# It NEVER touches qport_auth or any qport_user_* schemas.
param(
  [string]$SourceDatabaseUrl = "postgresql://qport:qport@127.0.0.1:5432/qport",
  [string]$TargetDatabaseUrl = "postgresql://neondb_owner:npg_Ntf82skygwLR@ep-green-bread-awgd6hke.c-12.us-east-1.aws.neon.tech/neondb?sslmode=require",
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$pythonExe = if (Test-Path "$Root\.venv\Scripts\python.exe") { "$Root\.venv\Scripts\python.exe" } else { "python" }

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " QPORT SAFE FINANCE SYNC TO VERCEL/NEON" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Mode: " -NoNewline; if ($DryRun) { Write-Host "DRY-RUN (Preview only)" -ForegroundColor Yellow } else { Write-Host "TRANSACTIONAL UPSERT (Safe Sync)" -ForegroundColor Green }
Write-Host " Target Schema: qport_finance ONLY (User portfolios & accounts are 100% isolated)" -ForegroundColor Gray
Write-Host " Source: $SourceDatabaseUrl"
Write-Host " Target: $TargetDatabaseUrl"
Write-Host "==========================================================" -ForegroundColor Cyan

$argsList = @("scripts/finance_sync.py", "--source-url", $SourceDatabaseUrl, "--target-url", $TargetDatabaseUrl)
if ($DryRun) {
  $argsList += "--dry-run"
}

& $pythonExe $argsList
if ($LASTEXITCODE -eq 0) {
  Write-Host ""
  Write-Host "🎉 Sync completed successfully! User data remained 100% untouched." -ForegroundColor Green
} else {
  Write-Host ""
  Write-Host "❌ Sync failed." -ForegroundColor Red
  exit $LASTEXITCODE
}
