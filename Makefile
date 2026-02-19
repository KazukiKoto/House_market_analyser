.PHONY: help start stop restart rebuild logs shell clean scraper migrate-db-container status down up build init-db migrate-db test check-db check-docker pre-flight health build-frontend

# Default target
help:
	@echo #############################################################
	@echo #     House Market Analyser - Docker Management             #
	@echo #############################################################
	@echo.
	@echo PRIMARY COMMANDS:
	@echo   make start      - Start the containers
	@echo   make stop       - Stop the containers
	@echo   make restart    - Restart the containers
	@echo   make rebuild    - Rebuild and restart containers
	@echo   make status     - Show container status
	@echo   make logs       - View container logs
	@echo.
	@echo SETUP COMMANDS:
	@echo   make init-db    - Initialize the database
	@echo   make migrate-db - Migrate existing database to latest schema
	@echo   make build-frontend - Build React frontend locally
	@echo   make test       - Run comprehensive tests
	@echo   make pre-flight - Check prerequisites before starting
	@echo   make health     - Check if dashboard is healthy
	@echo.
	@echo UTILITY COMMANDS:
	@echo   make shell      - Access container shell
	@echo   make scraper    - Run the scraper inside container
	@echo   make clean      - Remove all containers and volumes
	@echo   make validate   - Validate docker-compose.yml
	@echo.
	@echo ADDITIONAL COMMANDS:
	@echo   make build      - Build containers without starting
	@echo   make down       - Stop and remove containers
	@echo   make stats      - Show resource usage
	@echo   make open       - Open dashboard in browser
	@echo   make help       - Show this help message
	@echo.
	@echo #############################################################

# =============================================================================
# TESTING AND INITIALIZATION
# =============================================================================

# Check if Docker is installed and running
check-docker:
	@echo.
	@echo ========================================
	@echo  Checking Docker Installation
	@echo ========================================
	@docker --version >nul 2>&1 || (echo [ERROR] Docker is not installed or not in PATH && exit 1)
	@echo [OK] Docker is installed
	@docker compose version >nul 2>&1 || (echo [ERROR] Docker Compose is not available && exit 1)
	@echo [OK] Docker Compose is available
	@docker info >nul 2>&1 || (echo [ERROR] Docker daemon is not running. Please start Docker Desktop. && exit 1)
	@echo [OK] Docker daemon is running
	@echo.

# Check if database file exists
check-db:
	@echo.
	@echo ========================================
	@echo  Checking Database
	@echo ========================================
	@powershell -Command "if (Test-Path 'properties.db') { Write-Host '[OK] Database file exists' } else { Write-Host '[WARNING] Database file not found. Run: make init-db' -ForegroundColor Yellow; exit 1 }"

# Initialize the database
init-db:
	@echo.
	@echo ========================================
	@echo  Initializing Database
	@echo ========================================
	@powershell -Command "if (Test-Path 'properties.db') { Write-Host '[INFO] Database already exists. Skipping creation.' -ForegroundColor Cyan } else { python init_db.py; if ($$?) { Write-Host '[SUCCESS] Database created successfully!' -ForegroundColor Green } else { Write-Host '[ERROR] Failed to create database' -ForegroundColor Red; exit 1 } }"
	@echo.

# Migrate existing database to latest schema
migrate-db:
	@echo.
	@echo ========================================
	@echo  Migrating Database Schema
	@echo ========================================
	@powershell -Command "if (Test-Path 'properties.db') { python migrate_db.py properties.db; if ($$?) { Write-Host '[SUCCESS] Database migrated successfully!' -ForegroundColor Green } else { Write-Host '[ERROR] Migration failed' -ForegroundColor Red; exit 1 } } else { Write-Host '[ERROR] Database not found. Run: make init-db first' -ForegroundColor Red; exit 1 }"
	@echo.

# Build frontend locally (optional, mainly for development)
build-frontend:
	@echo.
	@echo ========================================
	@echo  Building React Frontend
	@echo ========================================
	@powershell -Command "if (-not (Test-Path 'frontend/node_modules')) { Write-Host 'Installing npm dependencies...' -ForegroundColor Cyan; Set-Location frontend; npm install; Set-Location .. }"
	@powershell -Command "Write-Host 'Building frontend...' -ForegroundColor Cyan; Set-Location frontend; npm run build; Set-Location ..; if ($$?) { Write-Host '[SUCCESS] Frontend built successfully!' -ForegroundColor Green; Write-Host 'Static files are in the static/ directory' -ForegroundColor Cyan } else { Write-Host '[ERROR] Frontend build failed' -ForegroundColor Red; exit 1 }"
	@echo.

# Pre-flight checks before starting
pre-flight: check-docker
	@echo ========================================
	@echo  Running Pre-Flight Checks
	@echo ========================================
	@echo Checking configuration files...
	@powershell -Command "if (Test-Path 'docker-compose.yml') { Write-Host '[OK] docker-compose.yml found' } else { Write-Host '[ERROR] docker-compose.yml not found' -ForegroundColor Red; exit 1 }"
	@powershell -Command "if (Test-Path 'Dockerfile') { Write-Host '[OK] Dockerfile found' } else { Write-Host '[ERROR] Dockerfile not found' -ForegroundColor Red; exit 1 }"
	@powershell -Command "if (Test-Path 'requirements.txt') { Write-Host '[OK] requirements.txt found' } else { Write-Host '[ERROR] requirements.txt not found' -ForegroundColor Red; exit 1 }"
	@powershell -Command "if (Test-Path 'dashboard.py') { Write-Host '[OK] dashboard.py found' } else { Write-Host '[ERROR] dashboard.py not found' -ForegroundColor Red; exit 1 }"
	@powershell -Command "if (Test-Path 'init_db.py') { Write-Host '[OK] init_db.py found' } else { Write-Host '[ERROR] init_db.py not found' -ForegroundColor Red; exit 1 }"
	@powershell -Command "if (Test-Path 'frontend') { Write-Host '[OK] frontend directory found' } else { Write-Host '[ERROR] frontend directory not found' -ForegroundColor Red; exit 1 }"
	@echo Checking database...
	@powershell -Command "if (Test-Path 'properties.db') { Write-Host '[OK] Database exists' } else { Write-Host '[WARNING] Database not found. Creating it...' -ForegroundColor Yellow; python init_db.py }"
	@echo.
	@echo [SUCCESS] All pre-flight checks passed!
	@echo.

# Comprehensive test suite
test: check-docker
	@echo.
	@echo ========================================
	@echo  Running Tests
	@echo ========================================
	@echo.
	@echo [TEST 1/6] Checking Docker installation...
	@docker --version >nul 2>&1 && echo [PASS] Docker installed || (echo [FAIL] Docker not installed && exit 1)
	@echo.
	@echo [TEST 2/6] Checking Docker daemon...
	@docker info >nul 2>&1 && echo [PASS] Docker daemon running || (echo [FAIL] Docker daemon not running && exit 1)
	@echo.
	@echo [TEST 3/6] Validating docker-compose.yml...
	@docker compose config -q && echo [PASS] Configuration valid || (echo [FAIL] Configuration invalid && exit 1)
	@echo.
	@echo [TEST 4/6] Checking required files...
	@powershell -Command "$$files = @('dashboard.py', 'scraper.py', 'init_db.py', 'requirements.txt', 'Dockerfile', 'docker-compose.yml', 'frontend'); $$missing = @(); foreach ($$f in $$files) { if (-not (Test-Path $$f)) { $$missing += $$f } }; if ($$missing.Count -eq 0) { Write-Host '[PASS] All required files present' } else { Write-Host '[FAIL] Missing files:' $$missing -ForegroundColor Red; exit 1 }"
	@echo.
	@echo [TEST 5/6] Checking database...
	@powershell -Command "if (Test-Path 'properties.db') { Write-Host '[PASS] Database exists' } else { Write-Host '[WARNING] Database not found - will be created' -ForegroundColor Yellow }"
	@echo.
	@echo [TEST 6/6] Checking if port 8338 is available...
	@powershell -Command "$$conn = Test-NetConnection -ComputerName localhost -Port 8338 -WarningAction SilentlyContinue -InformationLevel Quiet; if (-not $$conn) { Write-Host '[PASS] Port 8338 is available' } else { Write-Host '[WARNING] Port 8338 is already in use' -ForegroundColor Yellow }"
	@echo.
	@echo ========================================
	@echo [SUCCESS] All tests passed!
	@echo ========================================
	@echo.

# =============================================================================
# CONTAINER MANAGEMENT
# =============================================================================

# Start containers
start: pre-flight
	@echo.
	@echo ========================================
	@echo  Starting House Market Dashboard
	@echo ========================================
	@docker compose up -d
	@echo.
	@echo [SUCCESS] Dashboard is running!
	@echo Visit: http://localhost:8338
	@echo.

# Alternative: start without detached mode
up:
	@echo.
	@echo ========================================
	@echo  Starting in Foreground Mode
	@echo ========================================
	@echo Press Ctrl+C to stop
	@echo.
	@docker compose up

# Build containers
build: check-docker
	@echo.
	@echo ========================================
	@echo  Building Docker Images
	@echo ========================================
	@docker compose build
	@if errorlevel 1 (echo [ERROR] Docker build failed! && exit 1)
	@echo.
	@echo [SUCCESS] Build complete!
	@echo.

# Stop containers
stop:
	@echo.
	@echo ========================================
	@echo  Stopping Containers
	@echo ========================================
	@docker compose stop
	@echo.
	@echo [SUCCESS] Containers stopped
	@echo.

# Stop and remove containers
down:
	@echo.
	@echo ========================================
	@echo  Stopping and Removing Containers
	@echo ========================================
	@docker compose down
	@echo.
	@echo [SUCCESS] Containers removed
	@echo.

# Restart containers
restart:
	@echo.
	@echo ========================================
	@echo  Restarting Containers
	@echo ========================================
	@docker compose restart
	@echo.
	@echo [SUCCESS] Containers restarted!
	@echo Visit: http://localhost:8338
	@echo.

# Rebuild containers (with build cache)
rebuild: pre-flight
	@echo.
	@echo ========================================
	@echo  Rebuilding and Starting Containers
	@echo ========================================
	@docker compose up -d --build
	@if errorlevel 1 (echo [ERROR] Rebuild failed! Check logs with: make logs && exit 1)
	@echo.
	@echo Waiting for container to be healthy...
	@timeout /t 5 /nobreak >nul
	@docker inspect house-market-dashboard --format="{{.State.Health.Status}}" 2>nul || echo Container starting...
	@echo.
	@echo [SUCCESS] Rebuild complete!
	@echo Visit: http://localhost:8338
	@echo.
	@echo.

# Force rebuild (no cache)
rebuild-no-cache:
	@echo.
	@echo ========================================
	@echo  Force Rebuilding (No Cache)
	@echo ========================================
	@docker compose build --no-cache
	@docker compose up -d
	@echo.
	@echo [SUCCESS] Force rebuild complete!
	@echo Visit: http://localhost:8338
	@echo.

# View logs in follow mode
logs:
	@echo.
	@echo ========================================
	@echo  Container Logs (Ctrl+C to exit)
	@echo ========================================
	@echo.
	@docker compose logs -f dashboard

# View last 100 lines of logs
logs-tail:
	@echo.
	@echo ========================================
	@echo  Last 100 Lines of Logs
	@echo ========================================
	@echo.
	@docker compose logs --tail=100 dashboard

# Access container shell
shell:
	@echo.
	@echo ========================================
	@echo  Accessing Container Shell
	@echo ========================================
	@echo Type 'exit' to return
	@echo.
	@docker compose exec dashboard /bin/bash

# Run scraper with arguments (usage: make scraper ARGS="--help")
scraper:
	@echo.
	@echo ========================================
	@echo  Running Scraper
	@echo ========================================
	@docker compose exec dashboard python scraper.py $(ARGS)
	@echo.

# Migrate database inside container
migrate-db-container:
	@echo.
	@echo ========================================
	@echo  Migrating Database in Container
	@echo ========================================
	@docker compose exec dashboard python /app/migrate_db.py /app/data/properties.db
	@echo.

# Show container status
status:
	@echo.
	@echo ========================================
	@echo  Container Status
	@echo ========================================
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>nul || docker compose ps
	@echo.
	@echo Health Status:
	@docker inspect house-market-dashboard --format="  Container: {{.Name}}" 2>nul || echo   [INFO] Container not found
	@docker inspect house-market-dashboard --format="  Status: {{.State.Status}}" 2>nul || echo   [INFO] Run 'make start' to start the container
	@docker inspect house-market-dashboard --format="  Health: {{.State.Health.Status}}" 2>nul || echo   [INFO] Health check not available
	@echo.
	@echo Dashboard URL: http://localhost:8338
	@echo Database: properties.db
	@powershell -Command "if (Test-Path 'properties.db') { Write-Host '  Database size:' -NoNewline; (Get-Item properties.db).Length / 1KB | ForEach-Object { Write-Host ([math]::Round($$_, 2)) 'KB' } } else { Write-Host '  [WARNING] Database not found' -ForegroundColor Yellow }"
	@echo.

# Health check command
health:
	@echo.
	@echo ========================================
	@echo  Health Check
	@echo ========================================
	@docker inspect house-market-dashboard --format="Container Status: {{.State.Status}}" 2>nul || (echo [ERROR] Container not running && exit 1)
	@docker inspect house-market-dashboard --format="Health Status: {{.State.Health.Status}}" 2>nul || echo Health checks not configured
	@echo Testing endpoint...
	@powershell -Command "try { $$response = Invoke-WebRequest -Uri 'http://localhost:8338' -TimeoutSec 5 -UseBasicParsing; if ($$response.StatusCode -eq 200) { Write-Host '[SUCCESS] Dashboard is responding!' -ForegroundColor Green } else { Write-Host '[WARNING] Unexpected status code:' $$response.StatusCode -ForegroundColor Yellow } } catch { Write-Host '[ERROR] Dashboard is not responding:' $$_.Exception.Message -ForegroundColor Red; exit 1 }"
	@echo.

# Clean everything (containers, networks, volumes, images)
clean:
	@echo.
	@echo ========================================
	@echo  Cleaning Up All Resources
	@echo ========================================
	@docker compose down -v --rmi local
	@echo.
	@echo [SUCCESS] Cleaned up everything!
	@echo.

# Clean only containers and networks (keep volumes)
clean-soft:
	@echo.
	@echo ========================================
	@echo  Cleaning Up (Preserving Volumes)
	@echo ========================================
	@docker compose down
	@echo.
	@echo [SUCCESS] Cleaned up (volumes preserved)
	@echo.

# Pull latest base images
pull:
	@echo.
	@echo ========================================
	@echo  Pulling Latest Images
	@echo ========================================
	@docker compose pull
	@echo.
	@echo [SUCCESS] Pull complete!
	@echo.

# Validate docker-compose.yml
validate:
	@echo.
	@echo ========================================
	@echo  Validating Configuration
	@echo ========================================
	@docker compose config -q && echo [SUCCESS] Configuration is valid! || echo [ERROR] Configuration has errors
	@echo.

# Show resource usage
stats:
	@echo.
	@echo ========================================
	@echo  Resource Usage (Ctrl+C to exit)
	@echo ========================================
	@echo.
	@docker stats house-market-dashboard

# Open dashboard in browser (requires start command first)
open:
	@echo.
	@echo ========================================
	@echo  Opening Dashboard
	@echo ========================================
	@echo URL: http://localhost:8338
	@echo.
	@start http://localhost:8338 || open http://localhost:8338 || xdg-open http://localhost:8338 2>nul || echo Please open http://localhost:8338 in your browser
	@echo.
