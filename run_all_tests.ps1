#!/usr/bin/env pwsh
<#
  run_all_tests.ps1
  Runs every layer of the StockSense test suite.
  Total expected time: ~10-20 minutes.
  Usage:  .\run_all_tests.ps1
#>

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pass = 0
$fail = 0

function Section($title) {
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host "=" * 60 -ForegroundColor Cyan
}

function Run($label, $command, $workdir) {
    Section $label
    Push-Location $workdir
    Invoke-Expression $command
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅  $label PASSED" -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host "❌  $label FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
        $script:fail++
    }
    Pop-Location
}

# ── 1. Analytics Core ─────────────────────────────────────────────────────────
Run "Core: Math, Engine, Anomaly, Forecast, Simulation" `
    "python -m pytest tests/ -v --tb=short -q" `
    "$root\core"

# ── 2. AI Module ──────────────────────────────────────────────────────────────
Run "AI: Mock provider, fallback, schema validation" `
    "python -m pytest tests/ -v --tb=short -q" `
    "$root\ai"

# ── 3. Backend — API contracts + integration ──────────────────────────────────
Run "Backend: Health, Datasets, SKUs, Scenarios, Auth, Error Envelopes" `
    "python -m pytest tests/ -v --tb=short -q" `
    "$root\backend"

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=" * 60 -ForegroundColor White
Write-Host "  RESULTS:  $pass suites PASSED  |  $fail suites FAILED" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Red" })
Write-Host "=" * 60 -ForegroundColor White

if ($fail -gt 0) { exit 1 }
