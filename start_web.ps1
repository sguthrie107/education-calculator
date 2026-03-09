# Start the education calculator web dashboard
# Usage: .\start_web.ps1

Write-Host "Starting Family Education Dashboard..." -ForegroundColor Green
Write-Host ""

# Check if virtual environment exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    . .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    . .\venv\Scripts\Activate.ps1
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    pip install -r requirements.txt
}

Write-Host ""
if (-not $env:HOST) { $env:HOST = "0.0.0.0" }
if (-not $env:PORT) { $env:PORT = "8001" }

Write-Host "Starting web server on http://localhost:$($env:PORT)" -ForegroundColor Green
Write-Host "Listening on $($env:HOST):$($env:PORT)" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the server (port 8001 to avoid conflict with retirement-calculator)
uvicorn app.main:app --reload --host $env:HOST --port $env:PORT
