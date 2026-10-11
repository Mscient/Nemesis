# dev.ps1 – Windows replacement for make on this project
# Usage: .\dev.ps1 [target]
# Default target: dev

param(
    [string]$Target = "dev"
)

function Invoke-Dev {
    Write-Host "🚀 Starting frontend + backend with hot reload..." -ForegroundColor Cyan
    docker compose up --build
}

function Invoke-Build {
    Write-Host "🔨 Building images..." -ForegroundColor Cyan
    docker compose build
}

function Invoke-Down {
    Write-Host "🛑 Stopping containers..." -ForegroundColor Yellow
    docker compose down
}

function Invoke-Logs {
    docker compose logs -f
}

function Invoke-Test {
    Write-Host "🧪 Running backend tests..." -ForegroundColor Cyan
    docker compose run --rm backend pytest -v
}

function Invoke-Lint {
    Write-Host "🔍 Running ruff (backend)..." -ForegroundColor Cyan
    docker compose run --rm backend ruff check app tests
    Write-Host "🔍 Running eslint (frontend)..." -ForegroundColor Cyan
    docker compose run --rm frontend pnpm lint
}

function Invoke-Seed {
    Write-Host "🌱 Seeding demo data..." -ForegroundColor Green
    docker compose run --rm backend python scripts/seed.py
}

function Invoke-ShellBackend {
    docker compose run --rm backend bash
}

function Invoke-ShellFrontend {
    docker compose run --rm frontend sh
}

function Invoke-Types {
    docker compose run --rm frontend sh /app/scripts/generate-types.sh
}

function Show-Help {
    Write-Host ""
    Write-Host "Available targets:" -ForegroundColor White
    Write-Host "  dev              Start both services with hot reload (default)"
    Write-Host "  build            Build images"
    Write-Host "  down             Stop containers"
    Write-Host "  logs             Tail all logs"
    Write-Host "  test             Run backend pytest"
    Write-Host "  lint             ruff + eslint"
    Write-Host "  seed             Insert demo data"
    Write-Host "  shell-backend    Shell into backend container"
    Write-Host "  shell-frontend   Shell into frontend container"
    Write-Host "  types            Regenerate TS types from OpenAPI"
    Write-Host "  help             Show this help"
    Write-Host ""
    Write-Host "Usage: .\dev.ps1 [target]" -ForegroundColor Gray
    Write-Host "Example: .\dev.ps1 seed" -ForegroundColor Gray
}

switch ($Target.ToLower()) {
    "dev"            { Invoke-Dev }
    "build"          { Invoke-Build }
    "down"           { Invoke-Down }
    "logs"           { Invoke-Logs }
    "test"           { Invoke-Test }
    "lint"           { Invoke-Lint }
    "seed"           { Invoke-Seed }
    "shell-backend"  { Invoke-ShellBackend }
    "shell-frontend" { Invoke-ShellFrontend }
    "types"          { Invoke-Types }
    "help"           { Show-Help }
    default {
        Write-Host "❌ Unknown target: $Target" -ForegroundColor Red
        Show-Help
        exit 1
    }
}
