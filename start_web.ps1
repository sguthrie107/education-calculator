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
    $hostAddress = "127.0.0.1"
    $portNumber = if ($env:PORT) { $env:PORT } else { "8001" }
    $url = "http://localhost:$portNumber"

    Write-Host "Starting web server on $url" -ForegroundColor Green
Write-Host "Listening on ${hostAddress}:${portNumber}" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

    try {
        Start-Process $url | Out-Null
    } catch {
        Write-Host "Could not auto-open browser. Open $url manually." -ForegroundColor Yellow
    }

# Start the server (port 8001 to avoid conflict with retirement-calculator)
    uvicorn app.main:app --reload --host $hostAddress --port $portNumber
