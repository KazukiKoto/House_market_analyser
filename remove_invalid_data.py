import sqlite3
import re

DB_PATH = r"d:\Projects\House_market_analyser\properties.db"

def is_valid_worcestershire_postcode(address):
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

def remove_invalid_postcodes(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, address FROM properties")
    invalid_ids = []
    for pid, address in cur.fetchall():
        if not is_valid_worcestershire_postcode(address):
            invalid_ids.append(pid)
    if invalid_ids:
        cur.executemany("DELETE FROM properties WHERE id = ?", [(pid,) for pid in invalid_ids])
    conn.commit()
    conn.close()
    print(f"Removed {len(invalid_ids)} properties with invalid Worcestershire postcode")

if __name__ == "__main__":
    remove_invalid_postcodes()

def report_invalid_postcodes(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, address FROM properties")
    invalid = []
    for pid, address in cur.fetchall():
        if not is_valid_worcestershire_postcode(address):
            invalid.append((pid, address))
    conn.close()
    print(f"Found {len(invalid)} properties with invalid Worcestershire postcode")
    for pid, address in invalid:
        print(f"ID: {pid} | Address: {address}")

if __name__ == "__main__":
    report_invalid_postcodes()
