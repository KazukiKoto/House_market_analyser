# Quick Start Script for Frontend Development

Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
Set-Location frontend
npm install

Write-Host "`nBuilding frontend..." -ForegroundColor Cyan
npm run build

Set-Location ..
Write-Host "`nFrontend built successfully!" -ForegroundColor Green
Write-Host "Static files are in the 'static' directory" -ForegroundColor Green
Write-Host "`nTo start the backend, run: python dashboard.py" -ForegroundColor Yellow
