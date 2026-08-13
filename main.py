"""CLI entry point for the Njuskalo apartment listing scraper."""
import argparse

import parser
import parser.scraper
import parser.storage
import plotext as plt
from rich.console import Console
from rich.rule import Rule
from rich.table import Table
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options


def make_driver():
    """Build a headless Firefox webdriver for scraping."""
    driver_config = parser.config["driver"]
    options = Options()
    options.add_argument("--headless")
    options.binary_location = driver_config["firefox_binary"]
    service = Service(driver_config["geckodriver"])
    return webdriver.Firefox(service=service, options=options)


def parse_args():
    """Parse and return CLI arguments."""
    defaults = parser.config["parser"]
    p = argparse.ArgumentParser(description="Njuskalo apartment parser")
    p.add_argument("--iter", action="store_true", help="Retry empty pages before skipping")
    p.add_argument(
        "--clean", action="store_true", help="Delete all previous listings from the database"
    )
    p.add_argument("--pages", type=int, default=100, help="Max pages to scrape (default: 100)")
    p.add_argument(
        "--min-price", type=int, default=defaults["min_price"],
        help="Override min price from config",
    )
    p.add_argument(
        "--max-price", type=int, default=defaults["max_price"],
        help="Override max price from config",
    )
    p.add_argument(
        "--min-square", type=int, default=defaults["min_square"],
        help="Override min square meters from config",
    )
    p.add_argument(
        "--max-square", type=int, default=defaults["max_square"],
        help="Override max square meters from config",
    )
    p.add_argument("--graph", action="store_true", help="Show price distribution chart")
    return p.parse_args()


def greetings(console):
    """Print the startup banner."""
    console.print(Rule("[bold]Njuskalo Apartment Parser[/bold]\n"))


def make_ad_printer(console):
    """
    STREAMING OUTPUT: returns a callback that scraper.collect_data calls
    right after it finds and saves new listings — the line appears in the
    terminal immediately, before the whole scrape finishes.
    """
    def on_new_ads(new_ads):
        for ad in new_ads:
            price = ad["price"] or "—"
            console.print(f"    [green]+[/green] {price:<12} [cyan]{ad['link']}[/cyan]")
    return on_new_ads


def output_table(collected_data, console):
    """Final summary table — printed once, after the whole scrape finishes."""
    if collected_data:
        console.print()

        table = Table(show_lines=True)
        table.add_column("Price", style="bold", no_wrap=True)
        table.add_column("Link", style="cyan")

        for item in collected_data:
            table.add_row(item["price"] or "—", item["link"])

        console.print(table)
        console.print()


def show_price_graph(console):
    """Print a terminal bar chart of the price distribution across all stored listings."""
    prices = [item["price"] for item in parser.storage.load_full_data() if item["price"]]

    if not prices:
        return

    bucket_start = (min(prices) // 100) * 100
    bucket_end = ((max(prices) // 100) + 1) * 100
    x_values, counts = [], []
    for start in range(bucket_start, bucket_end, 100):
        x_values.append(start + 50)
        counts.append(sum(1 for p in prices if start <= p < start + 100))

    console.print()
    plt.clf()
    plt.plot(x_values, counts, marker="braille")
    plt.title("Price distribution per 100€")
    plt.ylabel("Price range (€)")
    plt.xlabel("Listings")
    print(plt.build())

    console.input("\n[dim]Press Enter to exit...[/dim]")


def main():
    """Run the scraper end to end: parse args, scrape, print results."""
    flags = parse_args()
    console = Console()

    greetings(console)

    if flags.clean:
        removed = parser.storage.clean_data()
        console.print(f"[dim]Removed - {removed} previous listings[/dim]\n")

    driver = make_driver()
    on_new_ads = make_ad_printer(console)
    collected_data, _count_ads = parser.scraper.collect_data(
        driver, flags.pages, flags, retry=flags.iter, on_new_ads=on_new_ads
    )
    driver.quit()

    output_table(collected_data, console)

    if flags.graph:
        show_price_graph(console)


if __name__ == "__main__":
    main()
