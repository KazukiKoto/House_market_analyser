import requests
from bs4 import BeautifulSoup
import json


def main():
    url = 'https://www.onthemarket.com/for-sale/property/worcester/'
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; HouseMarketAnalyser/1.0)'}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f'Error fetching {url}: {e}')
        return

    soup = BeautifulSoup(resp.text, 'html.parser')

    # Look for property card patterns
    print('=== Looking for property cards ===')
    print(f'li.otm-PropertyCard: {len(soup.select("li.otm-PropertyCard"))}')
    print(f'ul.grid-list: {len(soup.select("ul.grid-list"))}')
    print(f'article tags: {len(soup.select("article"))}')
    print(f'div with itemprop: {len(soup.select("[itemprop]"))}')

    # Look at the first few property links
    print('\n=== Property detail links (first 5) ===')
    for i, a in enumerate(soup.select('a[href*="/details/"]')[:5]):
        print(f'{i+1}. href={a.get("href")} text={a.get_text(strip=True)[:60]}')

    # Check for JSON-LD structured data
    print('\n=== JSON-LD Structured Data ===')
    for script in soup.select('script[type="application/ld+json"]')[:2]:
        try:
            data = json.loads(script.string)
            print(f'Type: {data.get("@type")}')
            if isinstance(data, list):
                print(f'Array with {len(data)} items')
        except Exception:
            print('Failed to parse')

    # Sample a property card structure
    print('\n=== First card structure sample ===')
    # Try multiple selectors
    card = (soup.select_one('article') or
            soup.select_one('div[class*="property-card"]') or
            soup.select_one('div[itemtype*="Product"]') or
            soup.select_one('li[class*="property"]'))

    if card:
        print(f'Tag: {card.name}, Classes: {card.get("class")}')
        # Print the first 800 chars of HTML
        print(f'\nHTML snippet:\n{str(card)[:800]}')
    else:
        print('No property card found')
        # Let's look at the main container
        main_container = soup.select_one('main') or soup.select_one('[role="main"]') or soup.select_one('body > div')
        if main_container:
            print(f'\nMain container classes: {main_container.get("class")}')
            # Look for repetitive structures
            divs = main_container.find_all('div', recursive=False)
            print(f'Top-level divs in main: {len(divs)}')


if __name__ == '__main__':
    main()
