# House Market Dashboard - Frontend

This is a modern React + Tailwind CSS frontend for the House Market Dashboard with support for light/dark mode.

## Features

- 🎨 Modern UI with Tailwind CSS
- 🌓 Light/Dark mode toggle
- 📊 Interactive dashboard with statistics and charts
- 📱 Responsive design
- ⚡ Fast performance with Vite

## Development

### Prerequisites

- Node.js 18+ and npm

### Install Dependencies

```bash
cd frontend
npm install
```

### Run Development Server

```bash
npm run dev
```

This will start the Vite dev server on `http://localhost:3000` with hot module replacement.

The dev server is configured to proxy API requests to `http://localhost:8000`, so make sure the FastAPI backend is running.

### Build for Production

```bash
npm run build
```

This will create optimized production files in the `../static` directory, which the FastAPI backend will serve.

## Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable React components
│   │   ├── Navbar.jsx   # Navigation bar with dark mode toggle
│   │   ├── StatsPanel.jsx
│   │   ├── ChartsGrid.jsx
│   │   └── RecentListings.jsx
│   ├── pages/           # Page components
│   │   ├── Dashboard.jsx
│   │   ├── Houses.jsx
│   │   └── Assistant.jsx
│   ├── App.jsx          # Main app component
│   ├── main.jsx         # Entry point
│   └── index.css        # Global styles with Tailwind
├── index.html
├── package.json
├── vite.config.js       # Vite configuration
├── tailwind.config.js   # Tailwind CSS configuration
└── postcss.config.js    # PostCSS configuration
```

## Running the Full Application

1. Build the frontend:
   ```bash
   cd frontend
   npm install
   npm run build
   ```

2. Start the backend:
   ```bash
   cd ..
   python dashboard.py
   ```

3. Open your browser to `http://localhost:8000`

The backend will automatically serve the React app from the `static` directory.
