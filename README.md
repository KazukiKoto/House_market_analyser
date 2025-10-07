# House Market Analyser

A Python project for analyzing and visualizing house market data. It includes data scraping, dashboard visualization, and data cleaning tools.

## Features
- Scrapes property data and stores it in a local database
- Cleans and removes invalid data
- Interactive dashboard for data visualization
- HTML templates for web-based UI

## Project Structure
- `scraper.py`: Scrapes house market data
- `remove_invalid_data.py`: Cleans the database
- `dashboard.py`: Runs the dashboard and visualizations
- `templates/`: HTML templates for the dashboard
- `properties.db`: SQLite database storing property data

## Setup
1. Clone the repository:
   ```pwsh
   git clone <your-repo-url>
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

## Setting Up Scraper or Dashboard as a Startup Task
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
