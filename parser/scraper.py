"""Page scraping logic for njuskalo.hr apartment listings."""
import time
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from . import config, driver, storage

_console = Console()

seen_links = set()

def get_element_text(ad, by, value):
    """Get the text of an element."""
    try:
        return ad.find_element(by, value).text.strip()
    except NoSuchElementException:
        return None


def get_element_attr(ad, by, value, attr):
    """Get an attribute of an element."""
    try:
        return ad.find_element(by, value).get_attribute(attr)
    except NoSuchElementException:
        return None


def parse_listings(parse_driver):
    """Parse the listings on the current page."""
    ads = parse_driver.find_elements(By.CLASS_NAME, "EntityList-item")
    listings = []

    if not ads:
        return listings, 0
    for ad in ads:
        price = get_element_text(ad, By.CLASS_NAME, "price")
        link = get_element_attr(ad, By.TAG_NAME, "a", "href")
        if not link or not link.startswith("https://www.njuskalo.hr/nekretnine/") or link in seen_links:
            continue
        seen_links.add(link)
        listings.append({"price": price, "link": link})
    return listings, len(listings)


def collect_data(pages, retry=False):
    """Collect data from multiple pages."""
    all_data = []
    total_ads = 0
    empty_pages = 0
    previous_links = storage.load_previous_data()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=_console,
        transient=True,
    ) as progress:
        task = progress.add_task("[dim]Starting...[/dim]", total=None)
        for page in range(1, pages):
            progress.update(task, description=f"[dim]Scraping page {page}...[/dim]")
            min_price = config["parser"]["min_price"]
            max_price = config["parser"]["max_price"]
            min_square = config["parser"]["min_square"]
            max_square = config["parser"]["max_square"]
            url = (
                f"https://www.njuskalo.hr/iznajmljivanje-stanova/zagreb?"
                f"price[min]={min_price}&price[max]={max_price}"
                f"&livingArea[min]={min_square}&livingArea[max]={max_square}"
                f"&page={page}"
            )
            driver.get(url)
            data, _ = parse_listings(driver)
            if not data and retry:
                progress.update(task, description=f"[dim]Page {page} empty, retrying...[/dim]")
                time.sleep(2)
                driver.get(url)
                data, _ = parse_listings(driver)
            if not data:
                empty_pages += 1
                if empty_pages >= 2:
                    break
                continue
            unique_data = [ad for ad in data if ad["link"] not in previous_links]
            unique_count = len(unique_data)
            all_data.extend(unique_data)
            _console.print(f"  Page [bold]{page}[/bold]  [green]+{unique_count}[/green] new")
            total_ads += unique_count
            if unique_count == 0:
                empty_pages += 1
                if empty_pages >= 2:
                    break
            else:
                empty_pages = 0

    return all_data, total_ads