# PowerShell script encoding: UTF-8 with BOM
# ==============================================================================
# scripts.ps1 - PowerShell Development Scripts
# ==============================================================================
# This script provides convenient commands for common development tasks,
# similar to npm scripts.
#
# Usage:
#   .\scripts.ps1 <command> [parameters]
#
# Examples:
#   .\scripts.ps1 install              # Install dependencies
#   .\scripts.ps1 dev                  # Run development server
#   .\scripts.ps1 migrate -MESSAGE "Add users table"  # Create migration
#
# For a list of all available commands, run:
#   .\scripts.ps1 help
#   .\scripts.ps1                    # (no command also shows help)
#
# Note: This script is designed for Windows PowerShell. For Linux/Mac,
# ==============================================================================

<#
.SYNOPSIS
    Development script runner for B2B Supplier-Wholesale Exchange Platform

.DESCRIPTION
    Provides convenient commands for development tasks including:
    - Installing dependencies
    - Running the development server
    - Running code quality checks
    - Managing database migrations
    - Docker operations
    - And more...

.PARAMETER Command
    The command to execute (e.g., install, dev, lint, etc.)

.PARAMETER MESSAGE
    Optional message parameter (used for migration commands)

.EXAMPLE
    .\scripts.ps1 install
    Installs all dependencies

.EXAMPLE
    .\scripts.ps1 migrate -MESSAGE "Add users table"
    Creates a new database migration with the specified message
#>

[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [string]$Command = "help",

    [Parameter(Position=1)]
    [string]$MESSAGE = ""
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Helper function to check if a command exists
function Test-Command {
    param([string]$CommandName)
    $null -ne (Get-Command $CommandName -ErrorAction SilentlyContinue)
}

# Helper function to display error and exit
function Write-ErrorAndExit {
    param([string]$Message, [int]$ExitCode = 1)
    Write-Host $Message -ForegroundColor Red
    exit $ExitCode
}

# Helper function to run command with error handling
function Invoke-CommandSafe {
    param(
        [string]$Description,
        [string]$Command
    )
    Write-Host $Description -ForegroundColor Green
    try {
        Invoke-Expression $Command
        if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
            Write-ErrorAndExit "Command failed with exit code $LASTEXITCODE" $LASTEXITCODE
        }
    }
    catch {
        Write-ErrorAndExit "Error: $_" 1
    }
}

switch ($Command.ToLower()) {
    # ==========================================================================
    # Setup & Installation
    # ==========================================================================

    "install" {
        Invoke-CommandSafe "[*] Installing dependencies..." "pip install -r requirements.txt"
        Write-Host "[OK] Dependencies installed successfully" -ForegroundColor Green
    }

    "install-dev" {
        Invoke-CommandSafe "[*] Installing dependencies..." "pip install -r requirements.txt"
        Write-Host "[OK] Development environment ready!" -ForegroundColor Green
    }

    "setup-env" {
        if (Test-Path .env) {
            Write-Host "[!] .env file already exists. Skipping..." -ForegroundColor Yellow
        } else {
            if (Test-Path env.example) {
                Copy-Item env.example .env
                Write-Host "[OK] .env file created from env.example" -ForegroundColor Green
                Write-Host "[*] Please edit .env with your settings" -ForegroundColor Cyan
            } else {
                Write-ErrorAndExit "[ERROR] env.example file not found" 1
            }
        }
    }

    # ==========================================================================
    # Development Server
    # ==========================================================================

    "dev" {
        Write-Host "[*] Starting development server..." -ForegroundColor Green
        Write-Host "   Server will be available at http://localhost:8000" -ForegroundColor Cyan
        Write-Host "   API docs: http://localhost:8000/docs" -ForegroundColor Cyan
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    }

    "start" {
        Write-Host "[*] Starting production server..." -ForegroundColor Green
        uvicorn app.main:app --host 0.0.0.0 --port 8000
    }


    # ==========================================================================
    # Database Migrations
    # ==========================================================================

    "migrate" {
        if ($MESSAGE -eq "") {
            Write-Host "[ERROR] Error: MESSAGE parameter required" -ForegroundColor Red
            Write-Host "Usage: .\scripts.ps1 migrate -MESSAGE `"description`"" -ForegroundColor Yellow
            exit 1
        }
        Invoke-CommandSafe "[*] Creating migration..." "alembic revision --autogenerate -m `"$MESSAGE`""
    }

    "revision" {
        if ($MESSAGE -eq "") {
            Write-Host "[ERROR] Error: MESSAGE parameter required" -ForegroundColor Red
            Write-Host "Usage: .\scripts.ps1 revision -MESSAGE `"description`"" -ForegroundColor Yellow
            exit 1
        }
        Invoke-CommandSafe "[*] Creating migration..." "alembic revision --autogenerate -m `"$MESSAGE`""
    }

    "upgrade" {
        Invoke-CommandSafe "[*] Applying migrations..." "alembic upgrade head"
    }

    "downgrade" {
        Invoke-CommandSafe "[*] Rolling back one migration..." "alembic downgrade -1"
    }


    # ==========================================================================
    # Docker Operations
    # ==========================================================================

    "docker-build" {
        Invoke-CommandSafe "[*] Building Docker image..." "docker build -t swe-backend ."
    }

    "docker-up" {
        Invoke-CommandSafe "[*] Starting Docker Compose services..." "docker-compose up -d"
    }

    "docker-down" {
        Invoke-CommandSafe "[*] Stopping Docker Compose services..." "docker-compose down"
    }

    "docker-restart" {
        Invoke-CommandSafe "[*] Restarting Docker Compose services..." "docker-compose restart"
    }

    "docker-logs" {
        Write-Host "[*] Viewing Docker Compose logs (Ctrl+C to exit)..." -ForegroundColor Green
        docker-compose logs -f
    }

    "docker-shell" {
        Write-Host "[*] Opening shell in Docker container..." -ForegroundColor Green
        docker-compose exec app bash
    }

    "docker-clean" {
        Write-Host "[*] Cleaning Docker resources..." -ForegroundColor Green
        docker-compose down -v
        docker system prune -f
        Write-Host "[OK] Docker cleanup complete" -ForegroundColor Green
    }

    # ==========================================================================
    # Maintenance
    # ==========================================================================

    "clean" {
        Write-Host "[*] Cleaning cache and build files..." -ForegroundColor Green

        # Remove Python cache files
        Get-ChildItem -Path . -Include __pycache__,*.pyc -Recurse -Force -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

        # Remove build cache
        $cacheDirs = @("build", "dist")
        foreach ($dir in $cacheDirs) {
            if (Test-Path $dir) {
                Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
            }
        }

        # Remove egg-info directories
        Get-ChildItem -Path . -Filter *.egg-info -Directory -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

        Write-Host "[OK] Cleanup complete" -ForegroundColor Green
    }

    "clean-all" {
        Write-Host "[*] Performing deep cleanup..." -ForegroundColor Green
        & $PSScriptRoot\scripts.ps1 clean

        # Remove virtual environment (if exists)
        if (Test-Path .venv) {
            $response = Read-Host "Remove .venv directory? (y/N)"
            if ($response -eq "y" -or $response -eq "Y") {
                Remove-Item -Recurse -Force .venv
                Write-Host "[OK] Virtual environment removed" -ForegroundColor Green
            }
        }

        Write-Host "[OK] Deep cleanup complete" -ForegroundColor Green
    }

    # ==========================================================================
    # Help
    # ==========================================================================

    "help" {
        Write-Host ""
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host "          PowerShell Development Scripts - Available Commands" -ForegroundColor Cyan
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host ""

        Write-Host "[*] Setup & Installation:" -ForegroundColor Yellow
        Write-Host "  .\scripts.ps1 install          Install production dependencies" -ForegroundColor White
        Write-Host "  .\scripts.ps1 install-dev      Install dependencies" -ForegroundColor White
        Write-Host "  .\scripts.ps1 setup-env        Create .env file from env.example" -ForegroundColor White
        Write-Host ""

        Write-Host "[*] Development:" -ForegroundColor Yellow
        Write-Host "  .\scripts.ps1 dev              Run development server (hot reload)" -ForegroundColor White
        Write-Host "  .\scripts.ps1 start            Run production server" -ForegroundColor White
        Write-Host ""

        Write-Host "[*] Database:" -ForegroundColor Yellow
        Write-Host "  .\scripts.ps1 migrate -MESSAGE `"desc`"  Create new migration" -ForegroundColor White
        Write-Host "  .\scripts.ps1 revision -MESSAGE `"desc`"  Alias for migrate" -ForegroundColor White
        Write-Host "  .\scripts.ps1 upgrade            Apply all migrations" -ForegroundColor White
        Write-Host "  .\scripts.ps1 downgrade          Rollback one migration" -ForegroundColor White
        Write-Host ""

        Write-Host "[*] Docker:" -ForegroundColor Yellow
        Write-Host "  .\scripts.ps1 docker-build      Build Docker image" -ForegroundColor White
        Write-Host "  .\scripts.ps1 docker-up          Start Docker Compose services" -ForegroundColor White
        Write-Host "  .\scripts.ps1 docker-down        Stop Docker Compose services" -ForegroundColor White
        Write-Host "  .\scripts.ps1 docker-restart     Restart Docker Compose services" -ForegroundColor White
        Write-Host "  .\scripts.ps1 docker-logs        View Docker Compose logs" -ForegroundColor White
        Write-Host "  .\scripts.ps1 docker-shell      Open shell in Docker container" -ForegroundColor White
        Write-Host "  .\scripts.ps1 docker-clean       Clean Docker resources" -ForegroundColor White
        Write-Host ""

        Write-Host "[*] Maintenance:" -ForegroundColor Yellow
        Write-Host "  .\scripts.ps1 clean             Clean cache and build files" -ForegroundColor White
        Write-Host "  .\scripts.ps1 clean-all         Deep cleanup (includes .venv)" -ForegroundColor White
        Write-Host "  .\scripts.ps1 help              Show this help message" -ForegroundColor White
        Write-Host ""
    }

    default {
        Write-Host "[ERROR] Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        & $PSScriptRoot\scripts.ps1 help
        exit 1
    }
}
