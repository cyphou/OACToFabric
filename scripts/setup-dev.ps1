<#
.SYNOPSIS
    Development environment setup script for OAC-to-Fabric migration.

.DESCRIPTION
    Creates a Python virtual environment, installs dependencies, and
    configures the local development environment.

.EXAMPLE
    .\scripts\setup-dev.ps1
#>

param(
    [string]$PythonVersion = "3.12",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $RepoRoot) { $RepoRoot = Get-Location }

Write-Host "=== OAC-to-Fabric Development Setup ===" -ForegroundColor Cyan
Write-Host "Repository root: $RepoRoot"

# --- 1. Check Python ---
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python not found. Install Python $PythonVersion first." -ForegroundColor Red
    exit 1
}
$pyVer = & python --version 2>&1
Write-Host "Python: $pyVer"

# --- 2. Create virtual environment ---
$venvPath = Join-Path $RepoRoot ".venv"
if ((Test-Path $venvPath) -and -not $Force) {
    Write-Host "Virtual environment exists at $venvPath (use -Force to recreate)"
} else {
    Write-Host "Creating virtual environment..."
    if (Test-Path $venvPath) { Remove-Item -Recurse -Force $venvPath }
    & python -m venv $venvPath
    Write-Host "Created virtual environment at $venvPath" -ForegroundColor Green
}

# --- 3. Activate & install dependencies ---
$activate = Join-Path $venvPath "Scripts\Activate.ps1"
. $activate

Write-Host "Installing dependencies..."
& pip install --upgrade pip setuptools wheel

# Core dependencies
& pip install pydantic pydantic-settings httpx tenacity networkx lxml

# Testing
& pip install pytest pytest-asyncio pytest-cov

# Development tools
& pip install ruff black mypy

# Azure / Fabric SDKs (optional)
# & pip install azure-identity azure-mgmt-resource

Write-Host ""
Write-Host "Dependencies installed." -ForegroundColor Green

# --- 4. Create .env if missing ---
$envFile = Join-Path $RepoRoot ".env"
$envExample = Join-Path $RepoRoot ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile
    Write-Host "Created .env from .env.example — fill in your credentials." -ForegroundColor Yellow
}

# --- 5. Verify setup ---
Write-Host ""
Write-Host "=== Verification ===" -ForegroundColor Cyan
& python -c "import pydantic; print(f'pydantic {pydantic.__version__}')"
& python -c "import httpx; print(f'httpx {httpx.__version__}')"
& python -c "import pytest; print(f'pytest {pytest.__version__}')"

Write-Host ""
Write-Host "Setup complete! Activate the environment with:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Run tests with:"
Write-Host "  python -m pytest tests/ -v"
