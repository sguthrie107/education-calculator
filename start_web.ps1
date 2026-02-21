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
Write-Host "Starting web server on http://localhost:8001" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the server (port 8001 to avoid conflict with retirement-calculator)
uvicorn app.main:app --reload --port 8001
