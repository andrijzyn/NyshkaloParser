"""Typed settings loaded from config.toml.

No import-time side effects — call load_settings() explicitly.
"""
import tomllib
from dataclasses import dataclass
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config.toml"


@dataclass(frozen=True)
class ParserSettings:
    """Search filter defaults."""
    min_price: int
    max_price: int
    max_square: int
    min_square: int
    pages: int


@dataclass(frozen=True)
class SiteSettings:
    """Target site URL structure and CSS selectors."""
    base_url: str
    city: str
    listing_class: str
    price_class: str

    @property
    def listing_link_prefix(self) -> str:
        """URL prefix that a valid listing link must start with."""
        return f"{self.base_url}/nekretnine/"


@dataclass(frozen=True)
class ScrapingSettings:
    """Runtime scraping behavior."""
    headless: bool
    retry_sleep_seconds: float
    empty_page_limit: int


@dataclass(frozen=True)
class DriverSettings:
    """Selenium Firefox driver paths."""
    firefox_binary: str
    geckodriver: str


@dataclass(frozen=True)
class DatabaseSettings:
    """PostgreSQL connection settings."""
    dbname: str
    user: str
    host: str
    port: int
    password: str
    table: str


@dataclass(frozen=True)
class ReportSettings:
    """Terminal reporting/chart settings."""
    price_bucket_width: int


@dataclass(frozen=True)
class Settings:
    """All application settings, grouped by concern."""
    parser: ParserSettings
    site: SiteSettings
    scraping: ScrapingSettings
    driver: DriverSettings
    database: DatabaseSettings
    report: ReportSettings


def _section(raw: dict, name: str, path: Path) -> dict:
    try:
        return raw[name]
    except KeyError as e:
        raise SystemExit(f"config error: missing [{name}] section in {path}") from e


def _field(section: dict, key: str, section_name: str, path: Path):
    try:
        return section[key]
    except KeyError as e:
        raise SystemExit(
            f"config error: missing '{key}' under [{section_name}] in {path}"
        ) from e


def load_settings(path: Path | None = None) -> Settings:
    """Load and validate config.toml, returning a typed Settings object."""
    path = path or _DEFAULT_CONFIG_PATH

    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError as e:
        raise SystemExit(
            f"config error: {path} not found — copy config.example.toml to config.toml "
            "and fill in your values"
        ) from e

    def section(name: str) -> dict:
        return _section(raw, name, path)

    def field(sec: dict, key: str, sec_name: str):
        return _field(sec, key, sec_name, path)

    parser_sec = section("parser")
    site_sec = section("site")
    scraping_sec = section("scraping")
    driver_sec = section("driver")
    database_sec = section("database")
    report_sec = section("report")

    return Settings(
        parser=ParserSettings(
            min_price=field(parser_sec, "min_price", "parser"),
            max_price=field(parser_sec, "max_price", "parser"),
            max_square=field(parser_sec, "max_square", "parser"),
            min_square=field(parser_sec, "min_square", "parser"),
            pages=field(parser_sec, "pages", "parser"),
        ),
        site=SiteSettings(
            base_url=field(site_sec, "base_url", "site"),
            city=field(site_sec, "city", "site"),
            listing_class=field(site_sec, "listing_class", "site"),
            price_class=field(site_sec, "price_class", "site"),
        ),
        scraping=ScrapingSettings(
            headless=field(scraping_sec, "headless", "scraping"),
            retry_sleep_seconds=field(scraping_sec, "retry_sleep_seconds", "scraping"),
            empty_page_limit=field(scraping_sec, "empty_page_limit", "scraping"),
        ),
        driver=DriverSettings(
            firefox_binary=field(driver_sec, "firefox_binary", "driver"),
            geckodriver=field(driver_sec, "geckodriver", "driver"),
        ),
        database=DatabaseSettings(
            dbname=field(database_sec, "dbname", "database"),
            user=field(database_sec, "user", "database"),
            host=field(database_sec, "host", "database"),
            port=field(database_sec, "port", "database"),
            password=field(database_sec, "password", "database"),
            table=field(database_sec, "table", "database"),
        ),
        report=ReportSettings(
            price_bucket_width=field(report_sec, "price_bucket_width", "report"),
        ),
    )
