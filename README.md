# House Market Analyser

A Python project for analyzing and visualizing house market data. It includes data scraping, dashboard visualization, and data cleaning tools.

## Features
- **Robust web scraping**: Multi-strategy extraction adapts to page layout changes
- **Agent tracking & blacklist**: Automatically detects and filters out real estate agent addresses
- Scrapes property data and stores it in a local database
- **Automated scraping**: Runs automatically every hour and on application startup
- Cleans and removes invalid data
- **Modern React + Tailwind CSS UI**: Beautiful, responsive dashboard with dark/light mode
- Interactive charts and visualizations
- AI-powered property search assistant

> **Scraping Robustness**: The scraper uses a 3-tier fallback system (JSON-LD → URL patterns → Legacy selectors) that automatically adapts to website changes. See the scraper design notes and in-code documentation for more technical details.

> **Agent Address Filtering**: The scraper intelligently identifies real estate agent addresses using keyword detection and maintains a dynamic blacklist. When the same address appears frequently for one agent (3+ times), it's automatically blacklisted to improve address accuracy.

## Frontend
The project now features a modern React-based dashboard with:
- 🎨 Clean, responsive UI built with Tailwind CSS
- 🌓 Persistent dark/light mode toggle
- 📊 Interactive charts with lightbox view
- 🚀 Fast performance with Vite
- 📱 Mobile-friendly design

The frontend is automatically built during Docker build. For local development:

```bash
# Build frontend locally (optional)
make build-frontend

# Or manually
cd frontend
npm install
npm run build
```

The built static files are served by FastAPI from the `static/` directory.

## Project Structure
- `scraper.py`: Scrapes house market data with agent tracking and blacklist
- `scheduler.py`: Periodic scheduler for automated hourly scraping
- `init_db.py`: Database initialization with schema for properties and agent blacklist
- `dashboard.py`: Runs the dashboard and visualizations
- `templates/`: HTML templates for the dashboard
- `frontend/`: React-based modern UI with Tailwind CSS
- `properties.db`: SQLite database storing property data and agent blacklist

## Setup

### Option 1: Docker (Recommended)

The easiest way to run this project is using Docker:

#### Quick Start with Docker Compose

1. Clone the repository:
   ```bash
   git clone https://github.com/KazukiKoto/House_market_analyser
   cd House_market_analyser
   ```

2. Run tests and initialize (optional but recommended):
   ```bash
   # Using Makefile (recommended)
   make test       # Verify everything is set up correctly
   make init-db    # Initialize database if it doesn't exist
   
   # Or using Python directly
   python init_db.py
   ```

3. Build and start the container:
   ```bash
   # Using docker-compose directly
   docker-compose up -d
   
   # Or using Makefile (includes pre-flight checks)
   make start
   ```

4. Access the dashboard at `http://localhost:8338`

5. Stop the container:
   ```bash
   # Using docker-compose
   docker-compose down
   
   # Or using Makefile
   make stop
   ```

#### Using Makefile Commands (Recommended)

The project includes a Makefile for easy container management:

**Setup & Testing:**
```bash
make test          # Run comprehensive system tests
make init-db       # Initialize the database
make build-frontend # Build React frontend locally
make pre-flight    # Check all prerequisites
make health        # Check if dashboard is healthy
```

**Container Management:**
```bash
make start      # Start containers (with pre-flight checks)
make stop       # Stop containers
make restart    # Restart containers
make rebuild    # Rebuild and restart
make status     # Show detailed status
make logs       # View logs
```

**Utility:**
```bash
make shell      # Access container shell
make scraper    # Run the scraper
make clean      # Clean up everything
```

#### Using Docker CLI

1. Build the image:
   ```bash
   docker build -t house-market-analyser .
   ```

2. Run the container:
   ```bash
   docker run -d -p 8338:8000 -v $(pwd)/data:/app/data --name house-market house-market-analyser
   ```

   On Windows PowerShell:
   ```powershell
   docker run -d -p 8338:8000 -v ${PWD}/data:/app/data --name house-market house-market-analyser
   ```

#### Docker Configuration

**Data Persistence:** The `./data` directory is mounted as a volume, so databases persist on your host machine.

**Ollama Integration:** This application uses Ollama for AI features. Make sure Ollama is installed and running on your host machine:

1. **Download Ollama:** https://ollama.com/download
2. **Install Ollama** on your host machine
3. **Pull the required model:**
   ```bash
   ollama pull llama3.1
   ```
4. **Start Ollama** (usually runs automatically on installation)
   ```bash
   ollama serve  # If not running automatically
   ```
5. **Start the containers:**
   ```bash
   make start
   ```

The container will automatically connect to Ollama on your host via `host.docker.internal:11434`.

**Running the Scraper in Docker:**
```bash
docker-compose exec dashboard python scraper.py --help
# Or using Makefile
make scraper ARGS="--help"
```

**Development Commands:**
```bash
# Using Makefile (recommended)
make rebuild       # Rebuild and restart
make logs          # View logs
make shell         # Access shell
make scraper       # Run scraper

# Or using docker-compose directly
docker-compose up -d --build
docker-compose logs -f dashboard
docker-compose exec dashboard /bin/bash
```

**Troubleshooting:**
- If port 8338 is in use, change the port mapping in `docker-compose.yml` to a different port like `"8080:8000"`
- Ensure Ollama is running on your host machine
- On Linux, you may need `--network=host` instead of `host.docker.internal`

### Option 2: Local Python Installation

1. Clone the repository:
   ```pwsh
   git clone https://github.com/KazukiKoto/House_market_analyser
   ```
2. Install dependencies:
   ```pwsh
   pip install -r requirements.txt
   ```
3. Run the dashboard:
   ```pwsh
   python dashboard.py
   ```

## Usage
## Customizing Dashboard Graphs
You can add or remove graphs in the dashboard by editing `dashboard.py`:

### To Add a Graph:
1. Write a new function in `dashboard.py` that generates your desired plot (e.g., using matplotlib or plotly).
2. Add the function call to the dashboard route or template rendering logic.
3. Update the corresponding HTML template in `templates/dashboard.html` to display the new graph.

### To Remove a Graph:
1. Locate the function or code block in `dashboard.py` that creates the graph you want to remove.
2. Remove or comment out the function and any references to it in the dashboard route.
3. Remove the related section from `templates/dashboard.html`.

### Tips:
- Make sure each graph has a unique identifier in the template.
- Test your dashboard after changes to ensure everything displays correctly.
- You can use libraries like matplotlib, plotly, or seaborn for visualization.

## Customizing the Scraper for Your Own Dataset
If you want to build your own housing dataset by scraping other websites:

1. **Edit `scraper.py`:**
   - Update the URL(s) and parsing logic to match your target website's structure.
   - Use libraries like `requests` and `BeautifulSoup` for HTTP requests and HTML parsing.
   - Make sure to handle errors and respect website changes.

2. **Ethical Scraping Advice:**
   - Always check the website's Terms of Service and robots.txt before scraping.
   - Do not overload servers—use reasonable delays between requests.
   - Only collect publicly available data and avoid personal or sensitive information.
   - Attribute data sources if required and respect copyright.

3. **Testing:**
   - Test your changes on a small sample before running on large datasets.

## Automated Property Scraping

The application now includes **automated scraping** that runs:
- **On startup**: Initial scrape when the container starts (if database is empty)
- **Every hour**: Scheduled scrape runs automatically in the background

### Configuration

You can configure the scraping behavior using environment variables in `docker-compose.yml`:

```yaml
environment:
  # Auto-populate database with initial data on first run
  - AUTO_POPULATE=true  # Set to false to disable initial population
  
  # Enable periodic scraper scheduler (runs every hour)
  - ENABLE_SCHEDULER=true  # Set to false to disable hourly scraping
  
  # Scraping parameters (optional)
  - SCRAPE_LOCATION=worcester
  - SCRAPE_SITE=onthemarket
```

### Disabling Automated Scraping

If you prefer to run the scraper manually:

```yaml
environment:
  - AUTO_POPULATE=false      # Skip initial population
  - ENABLE_SCHEDULER=false   # Disable hourly scraping
```

Then run the scraper manually when needed:
```bash
make scraper
# Or with custom parameters
make scraper ARGS="--location birmingham --min-price 200000"
```

### Agent Address Blacklist

The scraper automatically tracks real estate agent addresses:
- Detects agent addresses using keyword patterns
- Maintains a blacklist of frequently-seen agent addresses
- When an address appears 3+ times for the same agent, it's blacklisted
- Blacklisted addresses are automatically excluded from property listings

This ensures you get accurate property addresses, not agent office locations.

## Setting Up Scraper or Dashboard as a Startup Task (Legacy)

> **Note:** With Docker deployment, automated scraping is now built-in (see section above). These instructions are for manual Python installations.

If you want to automate running the scraper or dashboard:

- **VS Code Task:**
  1. Open Command Palette > "Tasks: Configure Task".
  2. Add a task to run `python scraper.py` or `python dashboard.py`.
  3. You can set the task to run on folder open by configuring `"runOn": "folderOpen"` in `.vscode/tasks.json`.

- **Windows Startup:**
  1. Create a shortcut to `python scraper.py` or `python dashboard.py`.
  2. Place the shortcut in the Windows Startup folder (`shell:startup`).
  3. This will run the script every time you log in.

**Note:** For most users, it's best to run the scraper only when you need new data, not every time the project starts.

## License
This project is open-source. You are free to use, modify, and share it for personal, educational, or non-commercial purposes. Please use the code responsibly and ethically. For commercial use or redistribution get in contact with the author.
