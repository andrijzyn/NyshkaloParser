"""PostgreSQL-backed storage for scraped listings."""
# pylint: disable=no-member
# astroid can't resolve psycopg3's overloaded Connection.connect() return type,
# so it infers `conn` as a plain "value" and flags every conn.cursor()/commit() call.
import re

import psycopg
from psycopg import sql
from rich.console import Console

from .config import DatabaseSettings

_console = Console()


def extract_price(price):
    """Extracts an integer from a string like '300 €' — the DB price column is INTEGER."""
    if not price:
        return None
    match = re.search(r"\d+", price.replace(".", "").replace(",", ""))
    return int(match.group()) if match else None


class Storage:
    """Owns the PostgreSQL connection and all listing queries for one table."""

    def __init__(self, db_settings: DatabaseSettings):
        self.table = sql.Identifier(db_settings.table)
        try:
            self.conn: psycopg.Connection = psycopg.connect(
                dbname=db_settings.dbname,
                user=db_settings.user,
                host=db_settings.host,
                port=db_settings.port,
                password=db_settings.password or None,
            )
        except psycopg.OperationalError as e:
            _console.print(
                f"[red]✗ Could not connect to PostgreSQL database "
                f"'{db_settings.dbname}': {e}[/red]"
            )
            raise SystemExit(1) from e
        self._init_schema()

    def _init_schema(self):
        with self.conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {table} (
                        id SERIAL PRIMARY KEY,
                        price INTEGER,
                        url TEXT UNIQUE NOT NULL
                    )
                    """
                ).format(table=self.table)
            )
        self.conn.commit()

    def save_listings(self, listings):
        """Batch-inserts into the DB, ignoring duplicates by url."""
        with self.conn.cursor() as cur:
            cur.executemany(
                sql.SQL(
                    "INSERT INTO {table} (price, url) VALUES (%s, %s) "
                    "ON CONFLICT (url) DO NOTHING"
                ).format(table=self.table),
                [(extract_price(ad["price"]), ad["link"]) for ad in listings],
            )
        self.conn.commit()

    def load_previous_data(self):
        """Returns a set() of all urls already in the DB — filters during parsing."""
        with self.conn.cursor() as cur:
            cur.execute(sql.SQL("SELECT url FROM {table}").format(table=self.table))
            return {row[0] for row in cur.fetchall()}

    def load_full_data(self):
        """Returns every stored listing as {"price": int|None, "link": str}, cheapest first."""
        with self.conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT price, url FROM {table} ORDER BY price NULLS LAST").format(
                    table=self.table
                )
            )
            return [{"price": price, "link": url} for price, url in cur.fetchall()]

    def clean_data(self):
        """Deletes all stored listings; returns how many rows were removed."""
        with self.conn.cursor() as cur:
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {table}").format(table=self.table))
            count = cur.fetchone()[0]
            cur.execute(sql.SQL("TRUNCATE {table}").format(table=self.table))
        self.conn.commit()
        return count
