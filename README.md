# House Market Analyser

A Python project for analyzing and visualizing house market data. It includes data scraping, dashboard visualization, and data cleaning tools.

## Features
- Scrapes property data and stores it in a local database
- **Automated scraping**: Runs automatically every hour and on application startup
- Cleans and removes invalid data
- Interactive dashboard for data visualization
- HTML templates for web-based UI
- AI-powered property search assistant

## Project Structure
- `scraper.py`: Scrapes house market data
- `remove_invalid_data.py`: Cleans the database
- `dashboard.py`: Runs the dashboard and visualizations
- `templates/`: HTML templates for the dashboard
- `properties.db`: SQLite database storing property data

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
make test       # Run comprehensive system tests
make init-db    # Initialize the database
make pre-flight # Check all prerequisites
make health     # Check if dashboard is healthy
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

**Ollama Integration:** This application uses Ollama for AI features. You have two options:

- **Option A (Recommended):** Use Ollama on host machine
  - Container accesses it via `host.docker.internal:11434`
  - No additional configuration needed

- **Option B:** Run Ollama in Docker
  - Uncomment the `ollama` service section in `docker-compose.yml`
  - Update `OLLAMA_HOST=http://ollama:11434` in the environment variables

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
- Ensure Ollama is running on your host machine or configured in Docker
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
- **On startup**: Initial scrape when the container starts
- **Every hour**: Scheduled scrape runs automatically

You can configure the scraping behavior using environment variables. See [SCRAPING_AUTOMATION.md](SCRAPING_AUTOMATION.md) for detailed configuration options.

### Quick Configuration Example

Add these to your `docker-compose.yml` environment section:
```yaml
environment:
  - SCRAPER_LOCATION=worcester
  - SCRAPER_MIN_PRICE=200000
  - SCRAPER_MAX_PRICE=500000
  - SCRAPER_MIN_BEDS=3
```

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
