"""PostgreSQL-backed storage for scraped listings."""
# pylint: disable=no-member
# astroid can't resolve psycopg3's overloaded Connection.connect() return type,
# so it infers `conn` as a plain "value" and flags every conn.cursor()/commit() call.
import re
from rich.console import Console
import psycopg
from . import config

_console = Console()

_db = config["database"]

try:
    conn: psycopg.Connection = psycopg.connect(dbname=_db["dbname"], user=_db["user"])
except psycopg.OperationalError as e:
    _console.print(f"[red]✗ Could not connect to PostgreSQL database '{_db['dbname']}': {e}[/red]")
    raise SystemExit(1) from e


def _init_schema():
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS listings (
                id SERIAL PRIMARY KEY,
                price INTEGER,
                url TEXT UNIQUE NOT NULL
            )
            """
        )
    conn.commit()


_init_schema()


def extract_price(price):
    """Extracts an integer from a string like '300 €' — the DB price column is INTEGER."""
    if not price:
        return None
    match = re.search(r"\d+", price.replace(".", "").replace(",", ""))
    return int(match.group()) if match else None


def save_listings(listings):
    """Batch-inserts into the DB, ignoring duplicates by url."""
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO listings (price, url) VALUES (%s, %s) ON CONFLICT (url) DO NOTHING",
            [(extract_price(ad["price"]), ad["link"]) for ad in listings],
        )
    conn.commit()


def load_previous_data():
    """Returns a set() of all urls already in the DB — the source for filtering during parsing."""
    with conn.cursor() as cur:
        cur.execute("SELECT url FROM listings")
        return {row[0] for row in cur.fetchall()}


def load_full_data():
    """Returns every stored listing as {"price": int|None, "link": str}, cheapest first."""
    with conn.cursor() as cur:
        cur.execute("SELECT price, url FROM listings ORDER BY price NULLS LAST")
        return [{"price": price, "link": url} for price, url in cur.fetchall()]


def clean_data():
    """Deletes all stored listings; returns how many rows were removed."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM listings")
        count = cur.fetchone()[0]
        cur.execute("TRUNCATE listings")
    conn.commit()
    return count
