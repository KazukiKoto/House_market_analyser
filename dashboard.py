from fastapi import FastAPI, Query, HTTPException, Request, Body
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from io import BytesIO
from collections import Counter, defaultdict
from statistics import median, mean
from datetime import datetime
from fastapi.templating import Jinja2Templates
import os
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import base64
import json
import hashlib
import threading
import pickle
import requests
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_ollama import ChatOllama
from langchain_core.tools import Tool

##################################################
# config and app setup
##################################################

# DB_DEFAULT - use environment variable or default to relative path
DB_DEFAULT = os.environ.get("DB_DEFAULT", os.path.join(os.path.dirname(__file__), "properties.db"))

app = FastAPI(title="House Market Dashboard")

# middleware for local browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# configure templates directory for web pages
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

##################################################
# db helpers
##################################################

def get_conn(db_path: str = DB_DEFAULT):
    """
    Open a SQLite connection to the given database path.
    Args:
        db_path (str): Path to the SQLite database file.
    Returns:
        sqlite3.Connection: SQLite connection object with row_factory set to sqlite3.Row.
    Raises:
        FileNotFoundError: If the database file does not exist.
    """
    if not os.path.isabs(db_path): # Convert to absolute path if not already
        db_path = os.path.join(os.path.dirname(__file__), db_path)
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"DB not found: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def read_properties(db_path: str = DB_DEFAULT, include_off_market: bool = True) -> List[Dict[str, Any]]:
    """
    Read all properties from the database.
    Args:
        db_path (str): Path to the SQLite database file.
        include_off_market (bool): If True, include off-market properties.
    Returns:
        List[Dict[str, Any]]: List of property dictionaries with decoded JSON fields and numeric conversions.
    """
    conn = get_conn(db_path)
    cur = conn.cursor()
    if include_off_market:
        cur.execute("SELECT * FROM properties")
    else:
        cur.execute("SELECT * FROM properties WHERE on_market=1")
    rows = cur.fetchall()
    conn.close()
    props = []
    for r in rows:
        d = dict(r)
        try: # Decode JSON fields if present
            if d.get('images'):
                d['images'] = json.loads(d['images'])
        except Exception:
            d['images'] = []
        try:
            if d.get('summary'):
                d['summary'] = json.loads(d['summary'])
        except Exception:
            d['summary'] = {}
        for k in ('price', 'beds', 'sqft'): # Convert price, beds, sqft to integers if present
            if k in d and d[k] is not None:
                d[k] = int(d[k])
        props.append(d)
    return props

def png_response_from_fig(fig):
    """
    Convert a matplotlib figure to a StreamingResponse PNG.
    Args:
        fig (matplotlib.figure.Figure): The matplotlib figure.
    Returns:
        StreamingResponse: PNG image response.
    """
    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png', dpi=120)
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

def fig_to_png_bytes(fig, dpi=120):
    """
    Convert a matplotlib figure to PNG bytes.
    Args:
        fig (matplotlib.figure.Figure): The matplotlib figure.
        dpi (int): Dots per inch for the PNG.
    Returns:
        bytes: PNG image bytes.
    """
    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()

def fig_to_data_uri(fig):
    """
    Convert a matplotlib figure to a base64 data URI.
    Args:
        fig (matplotlib.figure.Figure): The matplotlib figure.
    Returns:
        str: Data URI string for the PNG image.
    """
    png = fig_to_png_bytes(fig)
    b64 = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{b64}"

def parse_iso_month(iso_str: Optional[str]) -> Optional[str]:
    """
    Parse an ISO date or datetime string and return 'YYYY-MM' format.
    Args:
        iso_str (Optional[str]): ISO date or datetime string.
    Returns:
        Optional[str]: Month string in 'YYYY-MM' format, or None if parsing fails.
    """
    if not iso_str:
        return None # expect ISO timestamp
    try:
        dt = datetime.fromisoformat(iso_str)
        return f"{dt.year:04d}-{dt.month:02d}"
    except Exception: # try parsing date-only if not ISO format
        try:
            dt = datetime.strptime(iso_str.split('T')[0], "%Y-%m-%d")
            return f"{dt.year:04d}-{dt.month:02d}"
        except Exception:
            return None

def parse_iso_datetime(iso_str: Optional[str]) -> Optional[datetime]:
    """
    Parse an ISO date or datetime string to a datetime object.
    Args:
        iso_str (Optional[str]): ISO date or datetime string.
    Returns:
        Optional[datetime]: Parsed datetime object, or None if parsing fails.
    """
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str)
    except Exception:
        try:
            return datetime.strptime(iso_str.split("T")[0], "%Y-%m-%d")
        except Exception:
            return None

def compute_stats(props: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute summary statistics for a list of properties.
    Args:
        props (List[Dict[str, Any]]): List of property dictionaries.
    Returns:
        Dict[str, Any]: Dictionary of computed statistics.
    """
    now = datetime.now()
    prices = [int(p["price"]) for p in props if p.get("price") is not None]
    sqfts = [int(p["sqft"]) for p in props if p.get("sqft") is not None]
    beds = [int(p["beds"]) for p in props if p.get("beds") is not None]
    total = len(props)
    on_market = sum(1 for p in props if p.get("on_market") == 1)
    lengths = []
    for p in props: # List lengths in days (first_seen -> last_seen or now)
        first = parse_iso_datetime(p.get("first_seen"))
        last = parse_iso_datetime(p.get("last_seen"))
        if not first:
            continue
        end = last or (now if p.get("on_market") == 1 else now)
        try:
            days = max(0, (end - first).days)
            lengths.append(days)
        except Exception:
            continue
    avg_listing_days = int(mean(lengths)) if lengths else None
    recent = sorted(props, key=lambda p: parse_iso_datetime(p.get("last_seen") or p.get("first_seen")) or datetime.min, reverse=True)
    return {
        "total": total,
        "on_market": on_market,
        "off_market": total - on_market,
        "avg_price": int(mean(prices)) if prices else None,
        "median_price": int(median(prices)) if prices else None,
        "avg_sqft": int(mean(sqfts)) if sqfts else None,
        "avg_beds": round(mean(beds), 2) if beds else None,
        "avg_listing_days": avg_listing_days,
        "recent": recent,
    }

##################################################
# graph creation
##################################################

def fig_price_trend(props):
    """
    Generate a line plot of median price by month.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    by_month = defaultdict(list)
    for p in props:
        month = parse_iso_month(p.get("last_seen") or p.get("first_seen"))
        price = p.get("price")
        if month and price:
            by_month[month].append(price)
    if not by_month:
        raise ValueError("No dated price data")
    months = sorted(by_month.keys())
    medians = [median(by_month[m]) for m in months]
    cmap = cm.get_cmap("viridis")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(months, medians, marker="o", color=cmap(0.6))
    ax.set_title("Median price by month")
    ax.set_xlabel("Month")
    ax.set_ylabel("Median Price (£)")
    ax.tick_params(axis="x", rotation=45)
    return fig

def fig_price_distribution(props, bins=30):
    """
    Generate a histogram of property prices.
    Args:
        props (list): List of property dicts.
        bins (int): Number of histogram bins.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    prices = [p["price"] for p in props if p.get("price") is not None]
    if not prices:
        raise ValueError("No price data")
    cmap = cm.get_cmap("viridis")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(prices, bins=bins, color=cmap(0.5), edgecolor="black")
    ax.set_title("Price distribution")
    ax.set_xlabel("Price (£)")
    ax.set_ylabel("Count")
    return fig

def fig_beds_distribution(props):
    """
    Generate a bar chart of bedroom counts.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    beds = [p["beds"] for p in props if p.get("beds") is not None]
    if not beds:
        raise ValueError("No beds data")
    cnt = Counter(beds)
    keys = sorted(cnt.keys())
    vals = [cnt[k] for k in keys]
    cmap = cm.get_cmap("viridis")
    colors = [cmap(i / max(1, len(keys) - 1)) for i in range(len(keys))]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([str(k) for k in keys], vals, color=colors)
    ax.set_title("Bedrooms distribution")
    ax.set_xlabel("Bedrooms")
    ax.set_ylabel("Count")
    return fig

def fig_property_type_share(props):
    """
    Generate a pie chart of property type share.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    types = [(p.get("property_type") or "unknown").lower() for p in props]
    if not types:
        raise ValueError("No property_type data")
    cnt = Counter(types)
    labels = list(cnt.keys())
    sizes = list(cnt.values())
    cmap = cm.get_cmap("viridis")
    colors = [cmap(i / max(1, len(labels) - 1)) for i in range(len(labels))]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=140, colors=colors)
    ax.set_title("Property type share")
    return fig

def fig_price_vs_sqft(props, max_points=1000):
    """
    Generate a scatter plot of price vs square footage.
    Args:
        props (list): List of property dicts.
        max_points (int): Maximum number of points to plot.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    points = [(p["sqft"], p["price"]) for p in props if p.get("sqft") and p.get("price")]
    if not points:
        raise ValueError("No sqft/price pairs")
    if len(points) > max_points:
        points = points[:max_points]
    xs = [pt[0] for pt in points]
    ys = [pt[1] for pt in points]
    cmap = cm.get_cmap("viridis")
    norm = plt.Normalize(min(ys), max(ys)) if ys else plt.Normalize(0, 1)
    fig, ax = plt.subplots(figsize=(8, 6))
    sc = ax.scatter(xs, ys, c=ys, cmap=cmap, norm=norm, alpha=0.7, s=25)
    ax.set_xlabel("Square feet")
    ax.set_ylabel("Price (£)")
    ax.set_title("Price vs Square footage")
    fig.colorbar(sc, ax=ax, label="Price (£)")
    return fig

def fig_price_vs_sqft_colored(props):
    """
    Generate a scatter plot of price vs sqft, colored by property type.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    import numpy as np
    types = list({(p.get("property_type") or "unknown").lower() for p in props})
    type_map = {t: i for i, t in enumerate(types)}
    xs, ys, cs, shapes = [], [], [], []
    for p in props:
        if p.get("sqft") and p.get("price"):
            xs.append(p["sqft"])
            ys.append(p["price"])
            cs.append(type_map.get((p.get("property_type") or "unknown").lower(), 0))
            shapes.append(p.get("beds", 0))
    cmap = cm.get_cmap("tab10", len(types))
    fig, ax = plt.subplots(figsize=(8, 6))
    sc = ax.scatter(xs, ys, c=cs, cmap=cmap, alpha=0.7, s=40, edgecolor='k')
    legend_labels = [plt.Line2D([0], [0], marker='o', color='w', label=t, markerfacecolor=cmap(i), markersize=8) for t, i in type_map.items()]
    ax.legend(handles=legend_labels, title="Property Type", bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.set_xlabel("Square Footage")
    ax.set_ylabel("Price (£)")
    ax.set_title("Price vs Square Footage (by Property Type)")
    return fig

def fig_price_per_sqft_vs_beds(props):
    """
    Generate a scatter plot of price per sqft vs number of bedrooms, colored by property type.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    xs, ys, cs = [], [], []
    types = list({(p.get("property_type") or "unknown").lower() for p in props})
    type_map = {t: i for i, t in enumerate(types)}
    for p in props:
        if p.get("sqft") and p.get("price") and p.get("beds"):
            xs.append(p["beds"])
            ys.append(p["price"] / p["sqft"])
            cs.append(type_map.get((p.get("property_type") or "unknown").lower(), 0))
    cmap = cm.get_cmap("tab10", len(types))
    fig, ax = plt.subplots(figsize=(8, 6))
    sc = ax.scatter(xs, ys, c=cs, cmap=cmap, alpha=0.7, s=40, edgecolor='k')
    legend_labels = [plt.Line2D([0], [0], marker='o', color='w', label=t, markerfacecolor=cmap(i), markersize=8) for t, i in type_map.items()]
    ax.legend(handles=legend_labels, title="Property Type", bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.set_xlabel("Number of Bedrooms")
    ax.set_ylabel("Price per Sqft (£)")
    ax.set_title("Price per Sqft vs Number of Bedrooms")
    return fig

def fig_boxplot_price_by_type(props):
    """
    Generate a boxplot of price by property type, excluding unknown, maisonette, studio.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    from matplotlib import ticker
    exclude_types = {"unknown", "maisonette", "studio"}
    types = sorted(
        t for t in {(p.get("property_type") or "unknown").lower() for p in props}
        if t not in exclude_types
    )
    data = []
    for t in types:
        data.append([
            p["price"]
            for p in props
            if (p.get("property_type") or "unknown").lower() == t
            and p.get("price")
        ])
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.boxplot(data, labels=types, showfliers=True)
    ax.set_xlabel("Property Type")
    ax.set_ylabel("Price (£)")
    ax.set_title("Price by Property Type")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"£{int(x):,}"))
    return fig

def fig_boxplot_ppsqft_by_type(props):
    """
    Generate a boxplot of price per sqft by property type, excluding unknown, maisonette, studio.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    from matplotlib import ticker
    exclude_types = {"unknown", "maisonette", "studio"}
    types = sorted(
        t for t in {(p.get("property_type") or "unknown").lower() for p in props}
        if t not in exclude_types
    )
    data = []
    for t in types:
        data.append([
            p["price"]/p["sqft"]
            for p in props
            if (p.get("property_type") or "unknown").lower() == t
            and p.get("price") and p.get("sqft")
        ])
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.boxplot(data, labels=types, showfliers=True)
    ax.set_xlabel("Property Type")
    ax.set_ylabel("Price per Sqft (£)")
    ax.set_title("Price per Sqft by Property Type")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"£{int(x):,}"))
    return fig

def fig_hist_sqft(props):
    """
    Generate a histogram of square footage.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    sqfts = [p["sqft"] for p in props if p.get("sqft")]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(sqfts, bins=30, color=cm.viridis(0.5), edgecolor="black")
    ax.set_title("Square Footage Distribution")
    ax.set_xlabel("Square Footage")
    ax.set_ylabel("Count")
    return fig

def fig_hist_price(props):
    """
    Generate a histogram of property prices.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    prices = [p["price"] for p in props if p.get("price")]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(prices, bins=30, color=cm.viridis(0.7), edgecolor="black")
    ax.set_title("Price Distribution")
    ax.set_xlabel("Price (£)")
    ax.set_ylabel("Count")
    return fig

def fig_bar_avg_price_by_beds(props):
    """
    Generate a bar chart of average price by number of bedrooms and property type.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    import numpy as np
    bed_types = sorted({p.get("beds") for p in props if p.get("beds") is not None})
    type_set = sorted({(p.get("property_type") or "unknown").lower() for p in props})
    data = {t: [] for t in type_set}
    for t in type_set:
        for b in bed_types:
            vals = [p["price"] for p in props if (p.get("property_type") or "unknown").lower() == t and p.get("beds") == b and p.get("price")]
            data[t].append(np.mean(vals) if vals else 0)
    x = np.arange(len(bed_types))
    width = 0.8 / max(1, len(type_set))
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, t in enumerate(type_set):
        ax.bar(x + i*width, data[t], width, label=t)
    ax.set_xticks(x + width*(len(type_set)-1)/2)
    ax.set_xticklabels([str(b) for b in bed_types])
    ax.set_xlabel("Number of Bedrooms")
    ax.set_ylabel("Average Price (£)")
    ax.set_title("Average Price by Number of Bedrooms and Property Type")
    ax.legend(title="Property Type")
    return fig

def fig_line_price_time(props):
    """
    Generate a line chart of average price per month by property type, excluding unknown, maisonette, studio.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    from collections import defaultdict
    exclude_types = {"unknown", "maisonette", "studio"}
    by_type_month = defaultdict(lambda: defaultdict(list))
    for p in props:
        t = (p.get("property_type") or "unknown").lower()
        if t in exclude_types:
            continue
        m = parse_iso_month(p.get("last_seen") or p.get("first_seen"))
        if m and p.get("price"):
            by_type_month[t][m].append(p["price"])
    fig, ax = plt.subplots(figsize=(10, 5))
    for t, months in by_type_month.items():
        sorted_months = sorted(months.keys())
        avg_prices = [mean(months[m]) for m in sorted_months]
        ax.plot(sorted_months, avg_prices, marker="o", label=t)
    ax.set_xlabel("Month")
    ax.set_ylabel("Average Price (£)")
    ax.set_title("Average Price Over Time by Property Type")
    ax.legend(title="Property Type")
    ax.tick_params(axis="x", rotation=45)
    return fig

def fig_boxplot_sqft_by_type(props):
    """
    Generate a boxplot of square footage by property type, excluding unknown, maisonette, studio.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    exclude_types = {"unknown", "maisonette", "studio"}
    types = sorted(
        t for t in {(p.get("property_type") or "unknown").lower() for p in props}
        if t not in exclude_types
    )
    data = []
    for t in types:
        data.append([
            p["sqft"]
            for p in props
            if (p.get("property_type") or "unknown").lower() == t
            and p.get("sqft")
        ])
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.boxplot(data, labels=types, showfliers=True)
    ax.set_xlabel("Property Type")
    ax.set_ylabel("Square Footage")
    ax.set_title("Square Footage by Property Type")
    return fig

def fig_scatter_price_vs_beds(props):
    """
    Generate a scatter plot of price vs number of bedrooms, dot size = sqft, color = property type.
    Args:
        props (list): List of property dicts.
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    import numpy as np
    xs, ys, sizes, cs = [], [], [], []
    types = list({(p.get("property_type") or "unknown").lower() for p in props})
    type_map = {t: i for i, t in enumerate(types)}
    for p in props:
        if p.get("beds") and p.get("price"):
            xs.append(p["beds"])
            ys.append(p["price"])
            sizes.append(p.get("sqft", 50) or 50)
            cs.append(type_map.get((p.get("property_type") or "unknown").lower(), 0))
    cmap = cm.get_cmap("tab10", len(types))
    fig, ax = plt.subplots(figsize=(8, 6))
    sc = ax.scatter(xs, ys, c=cs, cmap=cmap, s=[max(30, s/10) for s in sizes], alpha=0.7, edgecolor='k')
    legend_labels = [plt.Line2D([0], [0], marker='o', color='w', label=t, markerfacecolor=cmap(i), markersize=8) for t, i in type_map.items()]
    ax.legend(handles=legend_labels, title="Property Type", bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.set_xlabel("Number of Bedrooms")
    ax.set_ylabel("Price (£)")
    ax.set_title("Price vs Number of Bedrooms (dot size = sqft)")
    return fig

##################################################
# cache for plot images based on db hash
##################################################

_plot_cache = None  # Will be loaded from disk if possible
_plot_cache_hash = None
_plot_cache_lock = threading.Lock()
_HASH_FILE = os.path.join(os.path.dirname(__file__), "dashboard_plot_cache_hash.txt")
_CACHE_FILE = os.path.join(os.path.dirname(__file__), "dashboard_plot_cache.pkl")

def load_plot_cache():
    """
    Load the plot cache from file if it exists.
    Returns:
        dict: The plot cache dictionary.
    """
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "rb") as f:
                cache = pickle.load(f)
                return cache
        except Exception:
            pass
    return {}

def save_plot_cache(cache):
    """
    Save the plot cache to file.
    Args:
        cache (dict): The plot cache dictionary.
    """
    try:
        with open(_CACHE_FILE, "wb") as f:
            pickle.dump(cache, f)
    except Exception:
        pass

def load_cached_hash():
    """
    Load the cached DB hash from file if it exists.
    Returns:
        str or None: The cached hash or None if not found.
    """
    if os.path.exists(_HASH_FILE):
        try:
            with open(_HASH_FILE, "r") as f:
                hash_val = f.read().strip()
                return hash_val
        except Exception:
            return None
    return None

def save_cached_hash(db_hash):
    """
    Save the DB hash to file.
    Args:
        db_hash (str): The hash to save.
    """
    try:
        with open(_HASH_FILE, "w") as f:
            f.write(db_hash or "")
    except Exception:
        pass

def hash_db_file(db_path):
    """
    Compute a SHA256 hash of the database file contents.
    Args:
        db_path (str): Path to the SQLite database file.
    Returns:
        str: Hexadecimal SHA256 hash of the file, or None if file not found.
    """
    if not os.path.isabs(db_path): # Convert to absolute path if not already
        db_path = os.path.join(os.path.dirname(__file__), db_path)
    if not os.path.exists(db_path):
        return None
    hasher = hashlib.sha256()
    with open(db_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def get_cached_plot(key, db_path, plot_func, *args, **kwargs):
    """
    Return cached plot data URI if db hash matches, else regenerate and cache.
    Args:
        key (str): Unique key for the plot.
        db_path (str): Path to the SQLite database file.
        plot_func (callable): Function to generate the plot.
        *args, **kwargs: Arguments for plot_func.
    Returns:
        str: Data URI for the plot image.
    """
    global _plot_cache, _plot_cache_hash
    db_hash = hash_db_file(db_path)
    # Load hash and plot cache from file if not already loaded
    if _plot_cache_hash is None:
        _plot_cache_hash = load_cached_hash()
    if _plot_cache is None:
        _plot_cache = load_plot_cache()
    with _plot_cache_lock:
        # Only clear cache and update hash if the hash has changed
        if _plot_cache_hash != db_hash:
            _plot_cache = {}
            _plot_cache_hash = db_hash
            save_cached_hash(db_hash)
            save_plot_cache(_plot_cache)
        entry = _plot_cache.get(key)
        if entry is not None:
            return entry
    # Not cached, regenerate
    fig = plot_func(*args, **kwargs)
    uri = fig_to_data_uri(fig)
    with _plot_cache_lock:
        _plot_cache[key] = uri
        save_plot_cache(_plot_cache)
    return uri

##################################################
# endpoints for graph creation
##################################################

@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: str = DB_DEFAULT, include_off_market: bool = True):
    """
    Render the dashboard page with summary statistics, plots, and recent listings.
    Args:
        request (Request): FastAPI request object.
        db (str): Path to the SQLite database file.
        include_off_market (bool): If True, include off-market properties.
    Returns:
        HTMLResponse: Rendered dashboard page.
    """
    props = read_properties(db, include_off_market=include_off_market)
    stats = compute_stats(props)

    # Use caching for plot URIs based on DB hash
    plot_uris = {}
    try: plot_uris['price_dist'] = get_cached_plot('price_dist', db, fig_price_distribution, props)
    except Exception: plot_uris['price_dist'] = None
    try: plot_uris['beds'] = get_cached_plot('beds', db, fig_beds_distribution, props)
    except Exception: plot_uris['beds'] = None
    try: plot_uris['ptype'] = get_cached_plot('ptype', db, fig_property_type_share, props)
    except Exception: plot_uris['ptype'] = None
    try: plot_uris['sqft'] = get_cached_plot('sqft', db, fig_price_vs_sqft, props)
    except Exception: plot_uris['sqft'] = None
    try: plot_uris['price_per_sqft_vs_beds'] = get_cached_plot('price_per_sqft_vs_beds', db, fig_price_per_sqft_vs_beds, props)
    except Exception: plot_uris['price_per_sqft_vs_beds'] = None
    try: plot_uris['boxplot_price_by_type'] = get_cached_plot('boxplot_price_by_type', db, fig_boxplot_price_by_type, props)
    except Exception: plot_uris['boxplot_price_by_type'] = None
    try: plot_uris['boxplot_ppsqft_by_type'] = get_cached_plot('boxplot_ppsqft_by_type', db, fig_boxplot_ppsqft_by_type, props)
    except Exception: plot_uris['boxplot_ppsqft_by_type'] = None
    try: plot_uris['hist_sqft'] = get_cached_plot('hist_sqft', db, fig_hist_sqft, props)
    except Exception: plot_uris['hist_sqft'] = None
    try: plot_uris['bar_avg_price_by_beds'] = get_cached_plot('bar_avg_price_by_beds', db, fig_bar_avg_price_by_beds, props)
    except Exception: plot_uris['bar_avg_price_by_beds'] = None
    try: plot_uris['line_price_time'] = get_cached_plot('line_price_time', db, fig_line_price_time, props)
    except Exception: plot_uris['line_price_time'] = None
    try: plot_uris['boxplot_sqft_by_type'] = get_cached_plot('boxplot_sqft_by_type', db, fig_boxplot_sqft_by_type, props)
    except Exception: plot_uris['boxplot_sqft_by_type'] = None
    try: plot_uris['scatter_price_vs_beds'] = get_cached_plot('scatter_price_vs_beds', db, fig_scatter_price_vs_beds, props)
    except Exception: plot_uris['scatter_price_vs_beds'] = None

    # helper to format money
    def fm(n):
        return f"£{n:,}" if n is not None else "n/a"

    # recent listings (max 20)
    recent_listings = []
    for p in stats["recent"][:20]:
        imgs = p.get("images") or []
        thumb = imgs[0] if imgs else ""
        price = fm(p.get("price"))
        beds = p.get("beds") or "-"
        sqft = p.get("sqft") or "-"
        addr = p.get("address") or p.get("title") or "No address"
        days = ""
        first = parse_iso_datetime(p.get("first_seen"))
        last = parse_iso_datetime(p.get("last_seen")) or (datetime.utcnow() if p.get("on_market") == 1 else None)
        if first:
            end = last or datetime.utcnow()
            try:
                days = f"{max(0, (end - first).days)} days"
            except Exception:
                days = ""
        recent_listings.append({
            "url": p.get("url") or "#",
            "thumb": thumb,
            "addr": addr,
            "price": price,
            "beds": beds,
            "sqft": sqft,
            "days": days
        })

    stats_html = []
    stats_html.append({"label": "Total listings", "value": stats['total']})
    stats_html.append({"label": "On market", "value": stats['on_market']})
    stats_html.append({"label": "Avg price", "value": fm(stats['avg_price'])})
    stats_html.append({"label": "Median price", "value": fm(stats['median_price'])})
    stats_html.append({"label": "Avg sqft", "value": stats['avg_sqft'] or 'n/a'})
    stats_html.append({"label": "Avg beds", "value": stats['avg_beds'] or 'n/a'})
    avg_listing_display = f"{stats['avg_listing_days']} days" if stats.get('avg_listing_days') else "n/a"
    stats_html.append({"label": "Avg listing length", "value": avg_listing_display})

    # Pass all data to the template
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "plot_uris": plot_uris,
        "stats_html": stats_html,
        "recent_listings": recent_listings
    })

@app.get("/plots/price_trend.png")
def price_trend(db: str = DB_DEFAULT, include_off_market: bool = True):
    """
    Endpoint to return the price trend plot as PNG.
    Args:
        db (str): Path to the SQLite database file.
        include_off_market (bool): If True, include off-market properties.
    Returns:
        StreamingResponse: PNG image response.
    """
    props = read_properties(db, include_off_market=include_off_market)
    try:
        fig = fig_price_trend(props)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return png_response_from_fig(fig)

@app.get("/plots/price_distribution.png")
def price_distribution(db: str = DB_DEFAULT, include_off_market: bool = True, bins: int = 30):
    """
    Endpoint to return the price distribution plot as PNG.
    Args:
        db (str): Path to the SQLite database file.
        include_off_market (bool): If True, include off-market properties.
        bins (int): Number of histogram bins.
    Returns:
        StreamingResponse: PNG image response.
    """
    props = read_properties(db, include_off_market=include_off_market)
    try:
        fig = fig_price_distribution(props, bins=bins)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return png_response_from_fig(fig)

@app.get("/plots/beds_distribution.png")
def beds_distribution(db: str = DB_DEFAULT, include_off_market: bool = True):
    """
    Endpoint to return the beds distribution plot as PNG.
    Args:
        db (str): Path to the SQLite database file.
        include_off_market (bool): If True, include off-market properties.
    Returns:
        StreamingResponse: PNG image response.
    """
    props = read_properties(db, include_off_market=include_off_market)
    try:
        fig = fig_beds_distribution(props)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return png_response_from_fig(fig)

@app.get("/plots/property_type_share.png")
def property_type_share(db: str = DB_DEFAULT, include_off_market: bool = True):
    """
    Endpoint to return the property type share plot as PNG.
    Args:
        db (str): Path to the SQLite database file.
        include_off_market (bool): If True, include off-market properties.
    Returns:
        StreamingResponse: PNG image response.
    """
    props = read_properties(db, include_off_market=include_off_market)
    try:
        fig = fig_property_type_share(props)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return png_response_from_fig(fig)

@app.get("/plots/price_vs_sqft.png")
def price_vs_sqft(db: str = DB_DEFAULT, include_off_market: bool = True, max_points: int = 1000):
    """
    Endpoint to return the price vs sqft plot as PNG.
    Args:
        db (str): Path to the SQLite database file.
        include_off_market (bool): If True, include off-market properties.
        max_points (int): Maximum number of points to plot.
    Returns:
        StreamingResponse: PNG image response.
    """
    props = read_properties(db, include_off_market=include_off_market)
    try:
        fig = fig_price_vs_sqft(props, max_points=max_points)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return png_response_from_fig(fig)

# add endpoints for the separate pages (renders templates/houses.html and templates/assistant.html)
@app.get("/houses", response_class=HTMLResponse)
def houses_page(
    request: Request,
    db: str = DB_DEFAULT,
    page: int = Query(1, ge=1),
    limit: int = Query(30),
    on_market: Optional[Any] = Query("true"),  # Default to "true" (on market)
    min_price: Optional[Any] = Query(None),
    max_price: Optional[Any] = Query(None),
    min_beds: Optional[Any] = Query(None),
    max_beds: Optional[Any] = Query(None),
    min_sqft: Optional[Any] = Query(None),
    max_sqft: Optional[Any] = Query(None),
    search: Optional[str] = None
):
    """
    Render the houses listing page with filters and pagination.
    Args:
        request (Request): FastAPI request object.
        db (str): Path to the SQLite database file.
        page (int): Page number.
        limit (int): Number of results per page.
        on_market (Optional[bool]): Filter by on_market status.
        min_price, max_price, min_beds, max_beds, min_sqft, max_sqft (Optional): Filter values.
        search (Optional[str]): Search string for address/title.
    Returns:
        HTMLResponse: Rendered houses listing page.
    """
    # Accept both string and integer inputs for filters
    def to_int(val):
        if val in (None, "", "None"):
            return None
        try:
            return int(val)
        except Exception:
            return None

    # Print raw incoming filter values for diagnosis
    print(f"[DIAG] Raw filter values: on_market={on_market}, min_price={min_price}, max_price={max_price}, min_beds={min_beds}, max_beds={max_beds}, min_sqft={min_sqft}, max_sqft={max_sqft}, search={search}")

    filters = []
    params = []
    min_price_val = to_int(min_price)
    max_price_val = to_int(max_price)
    min_beds_val = to_int(min_beds)
    max_beds_val = to_int(max_beds)
    min_sqft_val = to_int(min_sqft)
    max_sqft_val = to_int(max_sqft)

    print(f"[DIAG] Converted filter values: min_price={min_price_val}, max_price={max_price_val}, min_beds={min_beds_val}, max_beds={max_beds_val}, min_sqft={min_sqft_val}, max_sqft={max_sqft_val}")

    if min_price_val is not None:
        filters.append("price >= ?")
        params.append(min_price_val)
    if max_price_val is not None:
        filters.append("price <= ?")
        params.append(max_price_val)
    if min_beds_val is not None:
        filters.append("beds >= ?")
        params.append(min_beds_val)
    if max_beds_val is not None:
        filters.append("beds <= ?")
        params.append(max_beds_val)
    if min_sqft_val is not None:
        filters.append("sqft >= ?")
        params.append(min_sqft_val)
    if max_sqft_val is not None:
        filters.append("sqft <= ?")
        params.append(max_sqft_val)
    # Diagnose on_market value and conversion
    if on_market not in (None, "", "None"):
        val = str(on_market).lower()
        # Only apply filter if user explicitly set it
        if val in ("true", "1", "yes", "on"):
            filters.append("on_market = 1")
        elif val in ("false", "0", "no", "off"):
            filters.append("on_market = 0")
        # Do not append a parameter for on_market, just use the value directly
    if search not in (None, "", "None"):
        filters.append("(address LIKE ? OR title LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    # Query for all matching houses (no LIMIT/OFFSET)
    query_all = "SELECT * FROM properties"
    if filters:
        query_all += " WHERE " + " AND ".join(filters)
    query_all += " ORDER BY last_seen DESC"

    print(f"[DIAG] SQL Query (all): {query_all}")
    print(f"[DIAG] SQL Params (all): {params}")

    conn = get_conn(db)
    cur = conn.cursor()
    try:
        cur.execute(query_all, params)
        all_rows = cur.fetchall()
    except Exception as e:
        print(f"[DIAG] SQL execution error (all): {e}")
        all_rows = []
    conn.close()

    print(f"[DIAG] Total rows matching filters: {len(all_rows)}")

    # Pagination logic
    total_props = len(all_rows)
    total_pages = (total_props + limit - 1) // limit if total_props > 0 else 1

    # Clamp page to valid range
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_rows = all_rows[start_idx:end_idx]

    print(f"[DIAG] Paginated rows: {len(paginated_rows)} (page {page} of {total_pages})")

    # Convert rows to dicts and decode images/summary as in read_properties
    paginated_props = []
    for r in paginated_rows:
        d = dict(r)
        try:
            if d.get('images'):
                d['images'] = json.loads(d['images'])
        except Exception:
            d['images'] = []
        try:
            if d.get('summary'):
                d['summary'] = json.loads(d['summary'])
        except Exception:
            d['summary'] = {}
        for k in ('price', 'beds', 'sqft'):
            if k in d and d[k] is not None:
                d[k] = int(d[k])
        paginated_props.append(d)

    print(f"[DIAG] paginated_props count: {len(paginated_props)}")

    # Print a sample of the returned properties for diagnosis
    for idx, prop in enumerate(paginated_props[:3]):
        print(f"[DIAG] Sample property {idx+1}: {prop}")

    return templates.TemplateResponse("houses.html", {
        "request": request,
        "houses": paginated_props,
        "current_page": page,
        "total_pages": total_pages
    })

@app.get("/assistant", response_class=HTMLResponse)
def assistant_page(request: Request):
    """
    Render the AI assistant page (placeholder).
    Args:
        request (Request): FastAPI request object.
    Returns:
        HTMLResponse: Rendered assistant page.
    """
    return templates.TemplateResponse("assistant.html", {"request": request})

##################################################
# properties API
##################################################

@app.get("/api/properties")
def api_properties(db: str = DB_DEFAULT, on_market: Optional[bool] = None, limit: int = Query(200, ge=1, le=5000)):
    """
    API endpoint to return property data as JSON.
    Args:
        db (str): Path to the SQLite database file.
        on_market (Optional[bool]): Filter by on_market status.
        limit (int): Maximum number of results to return.
    Returns:
        JSONResponse: List of property dicts.
    """
    try:
        include = True if on_market is None else bool(on_market)
        props = read_properties(db, include_off_market=True)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    # filter by on_market when requested
    if on_market is True:
        props = [p for p in props if p.get('on_market') == 1]
    elif on_market is False:
        props = [p for p in props if p.get('on_market') == 0]
    # simple fields only
    out = []
    for p in props[:limit]:
        out.append({
            'id': p.get('id'),
            'url': p.get('url'),
            'title': p.get('title'),
            'price': p.get('price'),
            'beds': p.get('beds'),
            'sqft': p.get('sqft'),
            'property_type': p.get('property_type'),
            'address': p.get('address'),
            'on_market': bool(p.get('on_market'))
        })
    return JSONResponse(content=out)

##################################################
# LLM assistant and tool calls
##################################################

def filter_properties_tool(
    min_price=None, max_price=None,
    min_beds=None, max_beds=None,
    min_sqft=None, max_sqft=None,
    address_search=None, property_type=None
):
    print("[DEBUG] filter_properties_tool called with arguments:")
    print(f"  min_price={min_price} (type={type(min_price)})")
    print(f"  max_price={max_price} (type={type(max_price)})")
    print(f"  min_beds={min_beds} (type={type(min_beds)})")
    print(f"  max_beds={max_beds} (type={type(max_beds)})")
    print(f"  min_sqft={min_sqft} (type={type(min_sqft)})")
    print(f"  max_sqft={max_sqft} (type={type(max_sqft)})")
    print(f"  address_search={address_search} (type={type(address_search)})")
    print(f"  property_type={property_type} (type={type(property_type)})")
    props = read_properties(include_off_market=False)
    def match(p):
        def to_int(val):
            try:
                return int(val)
            except Exception:
                return None
        # Only filter if both filter and property value are not None
        if min_price is not None and p.get("price") is not None:
            if to_int(min_price) is not None and p["price"] < to_int(min_price): return False
        if max_price is not None and p.get("price") is not None:
            if to_int(max_price) is not None and p["price"] > to_int(max_price): return False
        if min_beds is not None and p.get("beds") is not None:
            if to_int(min_beds) is not None and p["beds"] < to_int(min_beds): return False
        if max_beds is not None and p.get("beds") is not None:
            if to_int(max_beds) is not None and p["beds"] > to_int(max_beds): return False
        if min_sqft is not None and p.get("sqft") is not None:
            if to_int(min_sqft) is not None and p["sqft"] < to_int(min_sqft): return False
        if max_sqft is not None and p.get("sqft") is not None:
            if to_int(max_sqft) is not None and p["sqft"] > to_int(max_sqft): return False
        if property_type is not None and property_type != "None":
            types = property_type if isinstance(property_type, list) else [property_type]
            types = [t.lower() for t in types if t is not None]
            if (p.get("property_type") or "").lower() not in types:
                return False
        if address_search and address_search != "None":
            if address_search.lower() not in (str(p.get("address") or "")).lower():
                return False
        return True
    filtered = [p for p in props if match(p)]
    result = []
    for p in filtered:
        result.append({
            "id": p.get("id"),
            "address": p.get("address"),
            "price": p.get("price"),
            "beds": p.get("beds"),
            "sqft": p.get("sqft"),
            "property_type": p.get("property_type"),
            "url": p.get("url"),
            "on_market": p.get("on_market"),
        })
    return result

filter_properties = Tool.from_function(
    name="filter_properties",
    description=(
        "Use this tool to search for properties in the database.\n"
        "Arguments:\n"
        "- min_price: minimum price in GBP (integer or None)\n"
        "- max_price: maximum price in GBP (integer or None)\n"
        "- min_beds: minimum number of bedrooms (integer or None)\n"
        "- max_beds: maximum number of bedrooms (integer or None)\n"
        "- min_sqft: minimum square footage (integer or None)\n"
        "- max_sqft: maximum square footage (integer or None)\n"
        "- address_search: a string to match in the address field (string or None)\n"
        "- property_type: filter by property type (string, one of 'detached', 'semi-detached', 'terraced', or None)\n"
        "If you do not want to filter by a field, set its value to None.\n"
        "You MUST use only these arguments and their exact names. Do NOT use any other arguments.\n"
        "Available property types are: detached, semi-detached, terraced.\n"
        "You MUST use this tool to answer any user request for properties, listings, or filtered results.\n"
        "Never make up properties. Only return properties from the database.\n"
        "You must never return properties that are not currently on the market (de-listed or sold).\n"
        "Use the 'address' field to refer to property listings."
    ),
    func=filter_properties_tool
)

@app.post("/api/assistant")
async def assistant_api(request: Request):
    """
    AI assistant endpoint. Uses Llama3.1 via Ollama to answer property queries and can filter properties.
    Accepts: JSON body with {"messages": [...]}
    Returns:
        JSON with reply and optionally filtered properties.
    """
    data = await request.json()
    messages = data.get("messages", [])
    user_prompt = messages[-1]["content"] if messages else ""

    system_prompt = (
        "You are an AI property search assistant for UK home buyers. "
        "You can answer questions and use tools to filter the property dataset. "
        "If the user asks for properties, listings, or anything that requires showing properties then you should use the 'filter_properties' tool. "
        "You should try to convert the user request into appropriate filter arguments for the tool before calling the tool. "
        "The filter_properties tool ONLY accepts these arguments: min_price, max_price, min_beds, max_beds, min_sqft, max_sqft, address_search, property_type. "
        "When you present properties, first speak freely to the user, then list properties in a markdown table with columns: Address | Price | Bedrooms | Square footage | Property type | Hyperlink. "
        "For the Hyperlink column, use the property 'url' as a clickable markdown link. "
        "Do NOT use any other argument names. Each argument is optional. "
        "For property_type, only use one of: detached, semi-detached, terraced. "
        "You shouldn't respond with JSON, only plain text and markdown tables. "
        "Do not use the property 'title' field in your response. Always use the 'address' field for property listings."
    )

    chat = ChatOllama(model="llama3.1").bind_tools([filter_properties])

    chat_history = [SystemMessage(system_prompt)]
    for msg in messages:
        chat_history.append(HumanMessage(msg["content"]))

    result = chat.invoke(chat_history)

    properties = []

    if hasattr(result, "tool_calls") and result.tool_calls:
        for call in result.tool_calls:
            tool_name = call.get("name")
            tool_args = call.get("args", {})
            tool_call_id = call.get("id")
            if tool_name == "filter_properties":
                try:
                    properties = filter_properties_tool(**tool_args)
                except Exception:
                    properties = []
        tool_message = ToolMessage(
            content=json.dumps(properties),
            tool_call_id=tool_call_id,
            name="filter_properties"
        )
        chat_history_for_response = [
            SystemMessage(system_prompt),
            HumanMessage(user_prompt),
            tool_message
        ]
        result2 = chat.invoke(chat_history_for_response)
        reply = result2.content
        if not reply or reply == "":
            reply = "I'm sorry, I couldn't generate a response based on the filtered properties."
    else:
        reply = getattr(result, "content", str(result))

    return {"reply": reply}

##################################################
# main
##################################################

if __name__ == "__main__":
    """
    Run the FastAPI dashboard app with Uvicorn.
    """
    import uvicorn
    print("Starting dashboard on http://127.0.0.1:8000")
    uvicorn.run("dashboard:app", host="127.0.0.1", port=8000, reload=False)