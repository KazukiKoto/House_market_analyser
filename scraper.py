import re
import os
import sys
import time
import argparse
import tempfile
from urllib.parse import urljoin, urlencode
import requests
from bs4 import BeautifulSoup
import json
import sqlite3
from datetime import datetime, timezone
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HouseMarketAnalyser/1.0; +https://example.com/bot)"
}

PRICE_RE = re.compile(r'£\s?([\d,]+)')
BEDS_RE = re.compile(r'(\d+)\s*(?:bed|beds|br|bedroom|bedrooms)\b', re.I)
SQFT_RE = re.compile(r'([\d,]+)\s*(?:sq\s*ft|sqft|ft²|sq\.)', re.I)

# Agent address detection keywords (used with whole-word matching to reduce false positives)
AGENT_KEYWORDS = [
    r'estate agents?', r'letting agents?',
    r'property agents?', r'sales & letting', r'sales and letting',
    r'branch office', r'head office',
    r'chartered surveyors?',
    r'\brics\b', r'\bnaea\b', r'\barla\b', r'\btpos\b', r'\bombudsman\b'
]


def is_agent_address(address_text):
    """
    Check if an address appears to be a real estate agency address
    rather than a property address.
    Returns True if the address contains agent-related keywords.
    """
    if not address_text:
        return False
    lower_text = address_text.lower()
    return any(re.search(keyword, lower_text) for keyword in AGENT_KEYWORDS)


def extract_agent_name(soup):
    """
    Extract the real estate agent/agency name from a property page.
    Returns agent name as string or None if not found.
    """
    # Try multiple strategies to find agent name
    # Strategy 1: Look for specific agent/office CSS selectors (avoid overly broad class-substring matches)
    agent_selectors = [
        '[data-test="agent-name"]', '.agent-name', '.office-name',
        'a[href*="/agent/"]', 'a[href*="/office/"]',
        '[data-test="branch-name"]', '.branch-name'
    ]
    
    for selector in agent_selectors:
        elem = soup.select_one(selector)
        if elem:
            agent_name = elem.get_text(strip=True)
            # Must be meaningful and not suspiciously long (avoid whole paragraphs)
            if agent_name and 3 < len(agent_name) <= 100:
                return agent_name
    
    # Strategy 2: Look for text patterns like "Marketed by..."
    page_text = soup.get_text(' ', strip=True)
    marketed_by = re.search(r'marketed by[:\s]+([A-Za-z0-9 &\'\-\.]+?)(?:,|\n|$)', page_text, re.I)
    if marketed_by:
        agent_name = marketed_by.group(1).strip()
        if agent_name and 3 < len(agent_name) <= 100:
            return agent_name
    
    return None


def update_agent_blacklist(conn, agent_name, address):
    """
    Update the agent blacklist with an agent name and address pair.
    Increments occurrence count if already exists.
    Returns True if address should be blacklisted (occurrence_count >= 3).
    """
    if not conn or not agent_name or not address:
        return False
    
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    
    # Check if this agent-address pair exists
    cur.execute(
        "SELECT occurrence_count FROM agent_blacklist WHERE agent_name = ? AND address = ?",
        (agent_name, address)
    )
    result = cur.fetchone()
    
    if result:
        # Increment count
        new_count = result[0] + 1
        cur.execute(
            "UPDATE agent_blacklist SET occurrence_count = ?, last_seen = ? WHERE agent_name = ? AND address = ?",
            (new_count, now, agent_name, address)
        )
        return new_count >= 3  # Blacklist threshold
    else:
        # Insert new entry
        cur.execute(
            "INSERT INTO agent_blacklist (agent_name, address, occurrence_count, first_seen, last_seen) VALUES (?, ?, 1, ?, ?)",
            (agent_name, address, now, now)
        )
        return False


def is_blacklisted_address(conn, address):
    """
    Check if an address is in the blacklist (occurrence_count >= 3).
    Returns True if blacklisted.
    """
    if not conn or not address:
        return False
    
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM agent_blacklist WHERE address = ? AND occurrence_count >= 3",
        (address,)
    )
    result = cur.fetchone()
    return result and result[0] > 0


def fetch(url, timeout=10):
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def normalize_price(text):
    m = PRICE_RE.search(text)
    if not m:
        return None
    return int(m.group(1).replace(',', ''))


def normalize_beds(text):
    m = BEDS_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def candidate_listing_anchors(soup):
    # Collect anchors that look like property links
    anchors = []
    for a in soup.select('a[href]'):
        href = a.get('href', '')
        if any(k in href for k in ['/property', '/property-for-sale', '/for-sale', '/property-details', '/properties']):
            anchors.append(a)
    return anchors

def _extract_json_ld_properties(soup, base_url=''):
    """
    Strategy 1: Extract properties from JSON-LD structured data.
    Most reliable but may not always be present.
    """
    properties = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string)
            # Handle both single objects and arrays
            items = data if isinstance(data, list) else [data]
            for item in items:
                # Only accept RealEstateListing or Product with specific property indicators
                item_type = item.get('@type', '')
                if item_type not in ['Product', 'RealEstateListing', 'Offer']:
                    continue

                # Validate it's actually a property listing
                # Check for URL and that it contains /details/ (property detail page)
                raw_url = item.get('url', '')
                if not raw_url or '/details/' not in raw_url:
                    continue
                url = urljoin(base_url, raw_url)

                # Parse price: JSON-LD offers.price may be a number or a formatted string
                offers = item.get('offers', {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                price_raw = offers.get('price') if isinstance(offers, dict) else None
                if isinstance(price_raw, (int, float)):
                    price = round(price_raw)
                elif isinstance(price_raw, str):
                    price = normalize_price(price_raw)
                else:
                    price = None

                prop = {
                    'url': url,
                    'title': item.get('name', ''),
                    'price': price,
                    'address': item.get('address', {}).get('streetAddress', '') if isinstance(item.get('address'), dict) else '',
                    'beds': None,
                    'images': [],
                    'id': None
                }

                # Only add if we have minimum viable data
                if prop['url']:
                    properties.append(prop)
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue
    return properties


def _extract_from_detail_links(soup, base_url):
    """
    Strategy 2: Find all /details/ links and extract surrounding context.
    Works even when page structure changes completely.
    """
    properties = []
    seen_urls = set()
    
    # Find all links to property detail pages
    for link in soup.select('a[href*="/details/"]'):
        href = link.get('href', '')
        if not href or '/details/' not in href:
            continue
            
        url = urljoin(base_url, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        # Extract property ID from URL
        m = re.search(r'/details/(\d+)/', href)
        pid = m.group(1) if m else None
        
        # Find the containing card/article/div (go up the tree)
        card = link
        for _ in range(10):  # Go up max 10 levels
            card = card.parent
            if not card:
                break
            # Stop if we found a likely container
            tag_name = card.name if hasattr(card, 'name') else ''
            if tag_name in ['article', 'li', 'section']:
                break
            # Or if it has property-related classes
            classes = ' '.join(card.get('class', [])).lower()
            if any(keyword in classes for keyword in ['property', 'card', 'listing', 'result']):
                break
        
        if not card:
            card = link.parent
        
        # Extract text content from the card
        card_text = card.get_text(' ', strip=True) if card else ''
        
        # Extract title - try multiple strategies
        title = ''
        # Try semantic markup first
        title_el = (card.select_one('[itemprop="name"]') or 
                   card.select_one('[itemprop="address"]') or
                   link)  # Fall back to link text
        if title_el:
            title = title_el.get_text(strip=True)
        
        # Extract price from card text
        price = normalize_price(card_text)
        
        # Extract beds from card text
        beds = normalize_beds(card_text)
        
        # Extract address - prefer semantic/CSS-based extraction, then fall back to heuristics
        # Filter out agent addresses
        address = ''
        candidate_addresses = []
        
        # Try semantic/CSS selectors
        address_els = (card.select('[itemprop="streetAddress"]') +
                       card.select('[itemprop="address"]') +
                       card.select('.address') +
                       card.select('[class*="address"]'))
        
        for addr_el in address_els:
            addr_text = addr_el.get_text(' ', strip=True)
            if addr_text and not is_agent_address(addr_text):
                candidate_addresses.append(addr_text)
        
        if candidate_addresses:
            # Prefer the first non-agent address
            address = candidate_addresses[0]
        else:
            # Fall back to heuristic search
            addr_indicators = [
                'road', 'street', 'avenue', 'drive', 'lane', 'close',
                'court', 'place', 'way', 'square', 'terrace', 'crescent',
                'park', 'gardens', 'rise'
            ]
            for text_node in card.find_all(string=True):
                text = text_node.strip()
                if not text:
                    continue
                lower_text = text.lower()
                if any(indicator in lower_text for indicator in addr_indicators):
                    if not is_agent_address(text):
                        address = text
                        break
        
        # Extract images
        images = set()
        for img in card.select('img[src], img[data-src]'):
            src = img.get('src') or img.get('data-src') or ''
            if src and 'data:image' not in src:  # Skip inline data URIs
                if ',' in src:  # Handle srcset
                    src = src.split(',')[0].strip().split(' ')[0]
                images.add(urljoin(base_url, src))
        
        properties.append({
            'id': pid or url,
            'url': url,
            'title': title or address or (f'Property {pid}' if pid is not None else url),
            'price': price,
            'beds': beds,
            'address': address,
            'images': sorted(images)
        })
    
    return properties


def _extract_legacy_format(soup, base_url):
    """
    Strategy 3: Try the old CSS selectors (for backward compatibility).
    """
    results = []
    container = soup.select_one('ul.grid-list-tabcontent, ul.grid-list')
    if container:
        cards = container.select('li.otm-PropertyCard, li.otm-PropertyCard.spotlight, li.otm-PropertyCard.premium')
    else:
        cards = soup.select('li.otm-PropertyCard')

    for card in cards:
        rel = None
        meta_url = card.select_one('meta[itemprop="url"]')
        if meta_url and meta_url.get('content'):
            rel = meta_url['content']
        else:
            a = card.select_one('a[href^="/details/"], a[href*="/details/"]')
            if a:
                rel = a.get('href')
        if not rel:
            continue
        url = urljoin(base_url, rel)

        title_el = card.select_one('[itemprop="name"]') or card.select_one('.title a') or card.select_one('.title')
        title = title_el.get_text(strip=True) if title_el else ''

        price_el = card.select_one('.otm-Price .price') or card.select_one('.price')
        price_text = price_el.get_text(' ', strip=True) if price_el else ''
        price = normalize_price(price_text or '')

        addr_el = card.select_one('span.address a') or card.select_one('span.address')
        address = addr_el.get_text(' ', strip=True) if addr_el else ''

        beds_el = card.select_one('[itemprop="numberOfBedrooms"]')
        beds = normalize_beds(beds_el.get_text(' ', strip=True)) if beds_el else None

        images = set()
        for img in card.select('img[itemprop="contentUrl"], img[src], img[data-src], img[data-srcset]'):
            src = img.get('src') or img.get('data-src') or img.get('data-srcset') or ''
            if not src:
                continue
            if ',' in src:
                src = src.split(',')[0].strip().split(' ')[0]
            images.add(urljoin(base_url, src))

        pid = None
        save_span = card.select_one('.save[data-property-id]')
        if save_span:
            pid = save_span.get('data-property-id')
        else:
            m = re.search(r'/details/(\d+)/', rel or '')
            if m:
                pid = m.group(1)

        results.append({
            'id': pid or url,
            'url': url,
            'title': title,
            'price': price,
            'beds': beds,
            'address': address,
            'images': sorted(images)
        })
    return results


def parse_search_results(soup, base_url):
    """
    ROBUST multi-strategy property extraction from OnTheMarket search results.
    
    Uses multiple extraction strategies in priority order:
    1. JSON-LD structured data (most reliable)
    2. URL pattern matching with context extraction (works with any layout)
    3. Legacy CSS selectors (backward compatibility)
    
    Returns list of dicts: id, url, title, price, beds, address, images
    """

    # Try Strategy 1: JSON-LD
    print('[Strategy 1] Trying JSON-LD extraction...', flush=True)
    results = _extract_json_ld_properties(soup, base_url)
    if results and any(r.get('price') is not None for r in results):
        print(f'[Strategy 1] [OK] Found {len(results)} properties via JSON-LD', flush=True)
        return results
    elif results:
        print('[Strategy 1] JSON-LD found but data incomplete, trying Strategy 2 to enrich...', flush=True)
    else:
        print('[Strategy 1] [FAIL] No JSON-LD data found', flush=True)

    # Try Strategy 2: Detail links with context
    print('[Strategy 2] Trying URL pattern matching...', flush=True)
    results = _extract_from_detail_links(soup, base_url)
    if results:
        print(f'[Strategy 2] [OK] Found {len(results)} properties via URL patterns', flush=True)
        return results
    print('[Strategy 2] [FAIL] No detail links found', flush=True)

    # Try Strategy 3: Legacy selectors
    print('[Strategy 3] Trying legacy CSS selectors...', flush=True)
    results = _extract_legacy_format(soup, base_url)
    if results:
        print(f'[Strategy 3] [OK] Found {len(results)} properties via legacy selectors', flush=True)
        return results
    print('[Strategy 3] [FAIL] Legacy selectors failed', flush=True)
    
    # If all strategies fail, log debugging info
    print('[ERROR] All extraction strategies failed!', flush=True)
    print(f'Page title: {soup.title.string if soup.title else "N/A"}', flush=True)
    print(f'Page length: {len(str(soup))} chars', flush=True)
    print(f'Links found: {len(soup.select("a[href]"))}', flush=True)
    print(f'Scripts found: {len(soup.select("script"))}', flush=True)
    
    return []


def dedupe_listings(listings):
    seen = set()
    out = []
    for l in listings:
        if l['url'] in seen:
            continue
        seen.add(l['url'])
        out.append(l)
    return out


def filter_listings(listings, min_price=None, max_price=None, min_beds=None):
    out = []
    for l in listings:
        if min_price is not None and (l['price'] is None or l['price'] < min_price):
            continue
        if max_price is not None and (l['price'] is None or l['price'] > max_price):
            continue
        if min_beds is not None and (l['beds'] is None or l['beds'] < min_beds):
            continue
        out.append(l)
    return out


def build_search_urls(site, location, pages=1):
    # keep only OnTheMarket behaviour (site param is accepted but only 'onthemarket' is supported)
    if site != 'onthemarket':
        raise ValueError('only onthemarket is supported in this version')
    urls = []
    loc = location.strip().lower().replace(' ', '-')
    # Example: https://www.onthemarket.com/for-sale/property/worcester/?page=2
    base = f'https://www.onthemarket.com/for-sale/property/{loc}/'
    for p in range(1, pages + 1):
        q = f'?page={p}' if p > 1 else ''
        urls.append(base + q)
    return urls


def get_total_results_from_soup(soup):
    """
    Find the total number of results on an OnTheMarket search page.
    Tries multiple strategies to extract the result count.
    """
    # Strategy 1: Try the explicit container first
    rc = soup.select_one('.otm-ResultCount')
    text = rc.get_text(' ', strip=True) if rc else None
    if text:
        m = re.search(r'([\d,]+)\s+results?', text, re.I)
        if m:
            count = int(m.group(1).replace(',', ''))
            print(f'[Total Results] Found {count} from .otm-ResultCount', flush=True)
            return count
    
    # Strategy 2: Search anywhere on the page
    page_text = soup.get_text(' ', strip=True)
    m = re.search(r'([\d,]+)\s+(?:results?|properties)', page_text, re.I)
    if m:
        count = int(m.group(1).replace(',', ''))
        print(f'[Total Results] Found {count} from page text', flush=True)
        return count
    
    # Strategy 3: Count the number of detail links as a minimum estimate
    detail_links = len(soup.select('a[href*="/details/"]'))
    if detail_links > 0:
        print(f'[Total Results] Could not find count, found {detail_links} properties on page', flush=True)
        # Don't return the count, let caller handle pagination differently
    else:
        print('[Total Results] Could not determine result count', flush=True)
    
    return None


def parse_property_details(soup, fallback=None, db_conn=None, db_lock=None):
    """
    Extract detailed fields from an OnTheMarket property page soup.
    Returns dict: price, property_type, beds, sqft, address, title, images, agent_name
    """
    out = {}

    # Extract agent name first
    agent_name = extract_agent_name(soup)
    out['agent_name'] = agent_name

    # title
    title_el = soup.select_one('h1[data-test="property-title"], h1.h4, h1')
    out['title'] = title_el.get_text(' ', strip=True) if title_el else (fallback.get('title') if fallback else '')

    # price (prefer data-test property-price)
    price_el = soup.select_one('[data-test="property-price"], .F79Qjm, .otm-Price .price')
    if price_el:
        out['price'] = normalize_price(price_el.get_text(' ', strip=True) or '')
    else:
        # fallback search anywhere
        t = soup.get_text(' ', strip=True)
        m = PRICE_RE.search(t)
        out['price'] = int(m.group(1).replace(',', '')) if m else (fallback.get('price') if fallback else None)

    # address - prioritize property addresses, filter out agent addresses
    # Keep blacklisted addresses as fallback instead of skipping them
    candidate_addresses = []
    blacklisted_addresses = []
    addr_els = soup.select('[itemprop="address"], .text-slate, .address, .otm-Title, [data-test="property-title"] + .text-slate')
    
    for addr_el in addr_els:
        addr_text = addr_el.get_text(' ', strip=True)
        if addr_text and not is_agent_address(addr_text):
            # Check if address is blacklisted (if db_conn available)
            is_blacklisted = False
            if db_conn:
                # Use db_lock for thread-safe reads consistent with write operations
                if db_lock:
                    with db_lock:
                        is_blacklisted = is_blacklisted_address(db_conn, addr_text)
                else:
                    is_blacklisted = is_blacklisted_address(db_conn, addr_text)
            if is_blacklisted:
                # Don't skip - keep as alternative
                blacklisted_addresses.append(addr_text)
            else:
                # Prefer non-blacklisted addresses
                candidate_addresses.append(addr_text)
    
    # Use best available address: non-blacklisted > blacklisted > fallback
    if candidate_addresses:
        # Use the first non-blacklisted address (best option)
        out['address'] = candidate_addresses[0]
    elif blacklisted_addresses:
        # Use blacklisted address if no alternatives (better than nothing)
        out['address'] = blacklisted_addresses[0]
    else:
        # Fall back to the fallback address if it's not an agent address
        fallback_addr = fallback.get('address') if fallback else ''
        if fallback_addr and not is_agent_address(fallback_addr):
            out['address'] = fallback_addr
        else:
            out['address'] = ''

    # beds (try itemprop or phrase on page)
    beds = None
    beds_el = soup.select_one('[itemprop="numberOfBedrooms"], .gdk9FE ~ .text-xs, .bed')
    if beds_el:
        beds = normalize_beds(beds_el.get_text(' ', strip=True) or '')
    if beds is None:
        m = BEDS_RE.search(soup.get_text(' ', strip=True))
        beds = int(m.group(1)) if m else (fallback.get('beds') if fallback else None)
    out['beds'] = beds

    # property type - look for common type words on the page near header or in content
    # IMPORTANT: Check longer compound types first to avoid false matches
    # (e.g., check 'semi-detached' before 'detached' to avoid misclassification)
    types = [
        'semi-detached', 'semi detached',  # Check compound types first
        'end-terrace', 'end terrace',
        'detached',  # Single types after compounds
        'terraced', 'terrace',
        'flat', 'maisonette', 'bungalow', 'studio',
        'semi'  # Fallback: standalone 'semi' normalizes to semi-detached
    ]
    page_text = soup.get_text(' ', strip=True).lower()
    ptype = None
    for t in types:
        if re.search(r'\b' + re.escape(t) + r'\b', page_text):
            # normalize the matched type
            if 'semi' in t:
                ptype = 'semi-detached'
            elif 'end' in t and 'terrace' in t:
                ptype = 'end-terraced'
            elif t in ('terrace', 'terraced'):
                ptype = 'terraced'
            else:
                ptype = t
            break
    out['property_type'] = ptype or None

    # sqft
    sqft = None
    m = SQFT_RE.search(page_text)
    if m:
        try:
            sqft = int(m.group(1).replace(',', ''))
        except ValueError:
            sqft = None
    out['sqft'] = sqft

    # images: collect large images if present
    images = set()
    for img in soup.select('img[src], img[data-src], img[data-srcset], picture img'):
        src = img.get('src') or img.get('data-src') or img.get('data-srcset') or ''
        if not src:
            continue
        if ',' in src:
            src = src.split(',')[0].strip().split(' ')[0]
        images.add(urljoin('https://www.onthemarket.com', src))
    out['images'] = sorted(images) if images else (fallback.get('images') if fallback else [])

    return out


def init_db(db_path):
    """Create SQLite DB and properties table if not exists."""
    # allow cross-thread use of the connection; we will serialize writes with a lock
    conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA busy_timeout=30000")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS properties (
        id TEXT PRIMARY KEY,
        url TEXT UNIQUE,
        name TEXT,
        title TEXT,
        price INTEGER,
        property_type TEXT,
        beds INTEGER,
        sqft INTEGER,
        address TEXT,
        agent_name TEXT,
        images TEXT,
        summary TEXT,
        first_seen TEXT,
        last_seen TEXT,
        off_market_at TEXT,
        on_market INTEGER DEFAULT 1,
        updated_at TEXT
    )
    """)
    
    # Create agent blacklist table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS agent_blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_name TEXT NOT NULL,
        address TEXT NOT NULL,
        occurrence_count INTEGER DEFAULT 1,
        first_seen TEXT,
        last_seen TEXT,
        UNIQUE(agent_name, address)
    )
    """)
    
    # index to speed title + address lookup
    cur.execute("CREATE INDEX IF NOT EXISTS idx_title_address ON properties(LOWER(title), LOWER(address))")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_address ON agent_blacklist(agent_name, address)")
    conn.commit()
    return conn


def _norm_text(s):
    if not s:
        return ''
    return re.sub(r'\s+', ' ', s.strip().lower())


def _run_with_db_retry(operation, max_retries=8, base_delay=0.1):
    """
    Retry SQLite operations that fail with transient lock errors.
    """
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if 'locked' not in msg and 'busy' not in msg:
                raise
            if attempt >= max_retries:
                raise
            sleep_s = min(2.0, base_delay * (2 ** attempt))
            time.sleep(sleep_s)


def _find_existing(conn, prop):
    """
    Return existing id (properties.id) if a matching record exists.
    Matching priority:
      1) title + address (if both present)
      2) title + property_type + beds + sqft (if address missing but title present)
      3) url
      4) id
    """
    cur = conn.cursor()

    # Prepare normalized title/address
    title = _norm_text(prop.get('title') or prop.get('name'))
    address = _norm_text(prop.get('address'))

    # 1) title + address (both must be present)
    if title and address:
        cur.execute(
            "SELECT id FROM properties WHERE LOWER(title)=? AND LOWER(address)=? LIMIT 1",
            (title, address)
        )
        r = cur.fetchone()
        if r:
            return r[0]

    # 2) address missing but title present -> match on title + property_type + beds + sqft
    if title and not address:
        ptype = (prop.get('property_type') or '').lower()
        beds = prop.get('beds')
        sqft = prop.get('sqft')
        cur.execute("""
            SELECT id FROM properties
            WHERE LOWER(title)=?
              AND LOWER(COALESCE(property_type, '')) = ?
              AND ( (beds IS NULL AND ? IS NULL) OR beds = ? )
              AND ( (sqft IS NULL AND ? IS NULL) OR sqft = ? )
            LIMIT 1
        """, (title, ptype, beds, beds, sqft, sqft))
        r = cur.fetchone()
        if r:
            return r[0]

    # 3) url
    url = prop.get('url')
    if url:
        cur.execute("SELECT id FROM properties WHERE url = ? LIMIT 1", (url,))
        r = cur.fetchone()
        if r:
            return r[0]

    # 4) id
    pid = prop.get('id')
    if pid:
        cur.execute("SELECT id FROM properties WHERE id = ? LIMIT 1", (str(pid),))
        r = cur.fetchone()
        if r:
            return r[0]

    return None


def validate_price(price):
    if price is not None and int(price) > 1000000:
        return False
    return True

def validate_worcestershire_postcode(address):
    """
    Returns True if the address contains a valid Worcestershire postcode.
    Accepts WR1-WR12, DY10-DY14, B60-B61, B96-B98, GL19, HR7-HR8.
    """
    if not address:
        return False
    postcode_patterns = [
        r'\bWR([1-9]|1[0-9])\b',
        r'\bDY1[0-4]\b',
        r'\bB6[01]\b',
        r'\bB9[6-8]\b',
        r'\bGL19\b',
        r'\bHR[78]\b'
    ]
    for pat in postcode_patterns:
        if re.search(pat, address, re.IGNORECASE):
            return True
    return False

def save_property(conn, prop):
    """
    Insert or update property into DB using app-level duplicate detection.
    When updating, update fields and set last_seen/on_market, clear off_market_at.
    """
    # Skip property if price is over 1,000,000
    if not validate_price(prop.get('price')):
        return None
    # Skip property if address does not contain a valid Worcestershire postcode
    if not validate_worcestershire_postcode(prop.get('address')):
        return None

    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    stored_id = str(prop.get('id') or prop.get('url'))
    # try to find existing DB id
    existing_id = _find_existing(conn, prop)
    images_json = json.dumps(prop.get('images') or [], ensure_ascii=False)
    summary_json = json.dumps(prop.get('summary') or {}, ensure_ascii=False)

    if existing_id:
        # update existing record
        cur.execute("""
            UPDATE properties SET
                id = ?,
                url = ?,
                name = ?,
                title = ?,
                price = ?,
                property_type = ?,
                beds = ?,
                sqft = ?,
                address = ?,
                agent_name = ?,
                images = ?,
                summary = ?,
                last_seen = ?,
                off_market_at = NULL,
                on_market = 1,
                updated_at = ?
            WHERE id = ?
        """, (
            stored_id,
            prop.get('url'),
            prop.get('name'),
            prop.get('title'),
            prop.get('price'),
            prop.get('property_type'),
            prop.get('beds'),
            prop.get('sqft'),
            prop.get('address'),
            prop.get('agent_name'),
            images_json,
            summary_json,
            now,
            now,
            existing_id
        ))
    else:
        # insert new record (first_seen = last_seen = now)
        cur.execute("""
            INSERT OR REPLACE INTO properties
              (id, url, name, title, price, property_type, beds, sqft, address, agent_name, images, summary, first_seen, last_seen, off_market_at, on_market, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stored_id,
            prop.get('url'),
            prop.get('name'),
            prop.get('title'),
            prop.get('price'),
            prop.get('property_type'),
            prop.get('beds'),
            prop.get('sqft'),
            prop.get('address'),
            prop.get('agent_name'),
            images_json,
            summary_json,
            now,
            now,
            None,
            1,
            now
        ))
    return stored_id


def mark_off_market(conn, seen_ids):
    """
    Mark rows that were previously on_market but not in seen_ids as off-market.
    Set off_market_at to now and on_market=0.
    """
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    # Build placeholders for NOT IN if any seen_ids, else mark all on_market rows off-market
    if seen_ids:
        placeholders = ','.join('?' for _ in seen_ids)
        sql = f"UPDATE properties SET on_market=0, off_market_at=?, updated_at=? WHERE on_market=1 AND id NOT IN ({placeholders})"
        params = [now, now] + list(seen_ids)
    else:
        sql = "UPDATE properties SET on_market=0, off_market_at=?, updated_at=? WHERE on_market=1"
        params = [now, now]
    cur.execute(sql, params)


def scrape(site, location, pages=1, min_price=None, max_price=None, min_beds=None, delay=1.0, db_conn=None, db_lock=None, max_workers=5):
    print(f'\n========================================', flush=True)
    print(f'Starting scrape: {site} / {location}', flush=True)
    print(f'Parameters: pages={pages}, min_price={min_price}, max_price={max_price}, min_beds={min_beds}', flush=True)
    print(f'========================================\n', flush=True)
    
    # Start by building only the first-page URL so we can read the total results
    first_urls = build_search_urls(site, location, pages=1)
    if not first_urls:
        print('[ERROR] Could not build search URLs', flush=True)
        return []

    listings = []

    # Fetch first page
    first_url = first_urls[0]
    print(f'[Page 1] Fetching {first_url}', flush=True)
    try:
        html = fetch(first_url)
        print(f'[Page 1] Received {len(html)} bytes', flush=True)
    except Exception as e:
        print(f'[ERROR] Failed to fetch {first_url}: {e}', flush=True)
        return []  # cannot proceed without first page
    
    soup = BeautifulSoup(html, 'html.parser')
    found = parse_search_results(soup, first_url)
    print(f'[Page 1] Extracted {len(found)} properties', flush=True)
    listings.extend(found)
    
    # If no results on first page, warn and abort
    if not found:
        print('[WARNING] No properties found on first page - aborting', flush=True)
        print('[DEBUG] Page title:', soup.title.string if soup.title else 'N/A', flush=True)
        # Save a debug copy of the HTML only when explicitly requested
        if os.environ.get('SCRAPER_DEBUG'):
            try:
                debug_path = os.path.join(tempfile.gettempdir(), 'debug_page.html')
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f'[DEBUG] Saved page HTML to {debug_path} for inspection', flush=True)
            except OSError as e:
                print(f'[DEBUG] Could not save debug HTML: {e}', flush=True)
        return []

    # Determine total results and total pages (30 per page)
    total = get_total_results_from_soup(soup)
    if total is None:
        # fallback to single page behaviour if we can't detect total
        total_pages = pages
        print(f'[Pagination] Using requested pages: {total_pages}', flush=True)
    else:
        per_page = 30
        total_pages = (total + per_page - 1) // per_page
        print(f'[Pagination] Total results: {total}, pages: {total_pages}', flush=True)

    # Build all page URLs
    all_urls = build_search_urls(site, location, pages=total_pages)
    print(f'[Pagination] Will fetch {len(all_urls)} pages', flush=True)

    # Fetch remaining pages (skip the first which we already fetched)
    for i, url in enumerate(all_urls[1:], start=2):
        print(f'[Page {i}] Fetching {url}', flush=True)
        try:
            html = fetch(url)
        except Exception as e:
            print(f'[Page {i}] ERROR: {e}', flush=True)
            continue
        soup = BeautifulSoup(html, 'html.parser')
        found = parse_search_results(soup, url)
        print(f'[Page {i}] Extracted {len(found)} properties', flush=True)
        listings.extend(found)
        time.sleep(delay)

    print(f'\n[Summary] Total properties extracted: {len(listings)}', flush=True)
    
    # Deduplicate search results by url
    before_dedup = len(listings)
    listings = dedupe_listings(listings)
    print(f'[Dedup] Removed {before_dedup - len(listings)} duplicates, {len(listings)} unique properties', flush=True)

    # Filter by price/beds as before (applies to summary price/beds)
    before_filter = len(listings)
    listings = filter_listings(listings, min_price=min_price, max_price=max_price, min_beds=min_beds)
    print(f'[Filter] Removed {before_filter - len(listings)} properties, {len(listings)} remain after filtering', flush=True)

    if not listings:
        print('[WARNING] No properties remaining after filtering', flush=True)
        return []

    # Now fetch each property page and enrich the data, printing progress and details as obtained
    print(f'\n[Details] Fetching detailed information for {len(listings)} properties...', flush=True)
    detailed = []
    seen_urls = set()
    seen_ids = set()
    total_listings = len(listings)

    # Ensure we have a lock for DB writes
    if db_conn and db_lock is None:
        db_lock = threading.Lock()

    # --- progress bar helpers ---
    import sys

    def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=40, fill='█'):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total))) if total else "100.0"
        filled_length = int(length * iteration // total) if total else length
        bar = fill * filled_length + '-' * (length - filled_length)
        sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
        sys.stdout.flush()
        if iteration == total:
            sys.stdout.write('\n')

    # worker that processes a single listing
    def process_listing(idx, l):
        url = l.get('url')
        try:
            prop_html = fetch(url)
            psoup = BeautifulSoup(prop_html, 'html.parser')
            details = parse_property_details(psoup, fallback=l, db_conn=db_conn, db_lock=db_lock)
            merged = {
                'id': l.get('id') or details.get('id') or url,
                'url': url,
                'name': details.get('title') or l.get('title') or url,
                'title': details.get('title') or l.get('title') or '',
                'price': details.get('price') if details.get('price') is not None else l.get('price'),
                'property_type': details.get('property_type'),
                'beds': details.get('beds') if details.get('beds') is not None else l.get('beds'),
                'sqft': details.get('sqft'),
                'address': details.get('address') or l.get('address'),
                'agent_name': details.get('agent_name'),
                'images': details.get('images') or l.get('images') or [],
                'summary': l
            }
            saved_id = None
            if db_conn:
                with db_lock:
                    def _write_listing():
                        with db_conn:
                            sid = save_property(db_conn, merged)
                            # Update blacklist tracking after saving, protected by db_lock
                            if merged.get('agent_name') and merged.get('address'):
                                update_agent_blacklist(db_conn, merged['agent_name'], merged['address'])
                            return sid
                    saved_id = _run_with_db_retry(_write_listing)
            if delay and delay > 0:
                time.sleep(delay)
            return merged, saved_id, True
        except Exception as e:
            merged = {
                'id': l.get('id') or url,
                'url': url,
                'name': l.get('title') or url,
                'title': l.get('title') or '',
                'price': l.get('price'),
                'property_type': None,
                'beds': l.get('beds'),
                'sqft': None,
                'address': l.get('address'),
                'images': l.get('images') or [],
                'summary': l
            }
            saved_id = None
            if db_conn:
                with db_lock:
                    def _write_fallback():
                        with db_conn:
                            return save_property(db_conn, merged)
                    saved_id = _run_with_db_retry(_write_fallback)
            if delay and delay > 0:
                time.sleep(delay)
            return merged, saved_id, False

    # submit tasks to thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {}
        idx = 0
        for l in listings:
            url = l.get('url')
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            idx += 1
            futures[ex.submit(process_listing, idx, l)] = url

        attempts = len(futures)
        success_count = 0
        completed = 0
        start_time = time.perf_counter()

        for fut in as_completed(futures):
            try:
                merged, sid, success = fut.result()
                detailed.append(merged)
                if sid:
                    seen_ids.add(sid)
                if success:
                    success_count += 1
            except Exception:
                pass
            completed += 1
            elapsed = time.perf_counter() - start_time
            print_progress_bar(completed, attempts, prefix='Progress', suffix=f'Elapsed: {elapsed:.1f}s', length=40)

    # summary check: attempts vs successes
    print(f'\n[Details] Property fetch attempts: {attempts}, successes: {success_count}', flush=True)
    if attempts != success_count:
        print(f'[Details] Warning: {attempts - success_count} properties failed to fetch details', flush=True)

    # After processing all properties, mark any previously on-market DB entries not seen this run as off-market
    if db_conn:
        try:
            with db_lock:
                def _mark_off_market():
                    with db_conn:
                        mark_off_market(db_conn, seen_ids)
                _run_with_db_retry(_mark_off_market)
            print(f'[Database] Updated on-market status for properties', flush=True)
        except Exception as e:
            print(f'[Database] ERROR marking off-market properties: {e}', flush=True)

    print(f'\n========================================', flush=True)
    print(f'SCRAPE COMPLETE', flush=True)
    print(f'Total properties found: {len(detailed)}', flush=True)
    if db_conn:
        print(f'Properties saved to database: {len(seen_ids)}', flush=True)
    print(f'========================================\n', flush=True)

    return detailed


def print_listings(listings):
    if not listings:
        print('No listings found.')
        return
    for i, l in enumerate(listings, 1):
        price = f"£{l['price']:,}" if l['price'] else 'N/A'
        beds = f"{l['beds']} bed" if l['beds'] else 'N/A'
        print(f"{i}. {l['title'] or l['url']}")
        print(f"   {price} | {beds}")
        print(f"   {l['url']}")

def _prompt_int(prompt_text, default=None):
    try:
        while True:
            s = input(prompt_text).strip()
            if s == '':
                return default
            try:
                return int(s)
            except ValueError:
                print("Please enter an integer or leave blank.")
    except (EOFError, KeyboardInterrupt):
        return default


def parse_args():
    p = argparse.ArgumentParser(description='Simple house listings scraper (OnTheMarket only)')
    # site option left for backward compat but default/fixed to onthemarket
    p.add_argument('--site', choices=['onthemarket'], required=False, default='onthemarket')
    p.add_argument('--location', required=False, default=None, help='Location slug or name e.g. Worcester')
    p.add_argument('--pages', type=int, default=1, help='Number of search result pages to scan')
    p.add_argument('--min-price', type=int, default=None)
    p.add_argument('--max-price', type=int, default=None)
    p.add_argument('--min-beds', type=int, default=None)
    p.add_argument('--db', required=False, default='properties.db',
                   help='Path to sqlite database file (default: properties.db in current directory)')
    p.add_argument('--non-interactive', action='store_true', 
                   help='Run without prompts (use defaults)')
    args = p.parse_args()

    # Only prompt interactively if stdin is a terminal and not in non-interactive mode
    is_interactive = sys.stdin.isatty() and not args.non_interactive
    
    # Interactive prompts for values not supplied on the CLI
    if is_interactive:
        try:
            if not args.location:
                loc = input("Location (e.g. Worcester) [required]: ").strip()
                args.location = loc or None

            # if still missing required, show help and exit cleanly
            if not args.location:
                p.print_help()
                raise SystemExit(0)

            # optional numeric prompts (press Enter to keep current/None)
            args.pages = _prompt_int(f"Pages [{args.pages}]: ", default=args.pages)
            args.min_price = _prompt_int(f"Min price [{args.min_price if args.min_price is not None else 'none'}]: ", default=args.min_price)
            args.max_price = _prompt_int(f"Max price [{args.max_price if args.max_price is not None else 'none'}]: ", default=args.max_price)
            args.min_beds = _prompt_int(f"Min beds [{args.min_beds if args.min_beds is not None else 'none'}]: ", default=args.min_beds)

        except (EOFError, KeyboardInterrupt):
            # if input is interrupted, exit gracefully
            print("\nInput cancelled.")
            raise SystemExit(0)
    else:
        # Non-interactive mode: use defaults if location not provided
        if not args.location:
            args.location = 'worcester'
            print(f"[INFO] Using default location: {args.location}", flush=True)

    return args


def run_scrape(
    db_path='properties.db',
    site='onthemarket',
    location='worcester',
    pages=None,
    min_price=None,
    max_price=None,
    min_beds=None,
    delay=1.0,
    max_workers=7
):
    """
    Programmatic entry point for other scripts.

    - db_path: path to sqlite DB (will be created if missing)
    - pages=None will let scrape auto-detect and fetch all pages when possible.
    Returns list of property dicts (same as scrape()).
    """
    db_conn = None
    try:
        db_conn = init_db(db_path)
    except Exception as e:
        print(f'Warning: failed to open/init DB {db_path}: {e}', flush=True)
        db_conn = None

    # If pages is None we pass pages=1 to allow scrape() to detect total pages.
    scrape_pages = 1 if pages is None else pages

    # create a DB lock for threaded access
    db_lock = threading.Lock() if db_conn else None

    # timing start
    start = time.perf_counter()
    results = scrape(
        site=site,
        location=location,
        pages=scrape_pages,
        min_price=min_price,
        max_price=max_price,
        min_beds=min_beds,
        delay=delay,
        db_conn=db_conn,
        db_lock=db_lock,
        max_workers=max_workers
    )
    # timing end
    elapsed = time.perf_counter() - start
    print(f'Run completed in {elapsed:.2f} seconds', flush=True)

    if db_conn:
        db_conn.close()
    return results


if __name__ == '__main__':
    # Parse command-line arguments
    args = parse_args()
    
    # Run scraper with provided arguments
    results = run_scrape(
        db_path=args.db,
        site=args.site,
        location=args.location,
        pages=args.pages if args.pages is not None else None,  # None -> auto-detect all pages
        min_price=args.min_price,
        max_price=args.max_price,
        min_beds=args.min_beds,
        delay=1.0,
        max_workers=7
    )
    print_listings(results)