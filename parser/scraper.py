"""Page scraping logic for njuskalo.hr apartment listings."""
import time
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from . import storage

_console = Console()


def get_element_text(ad, by, value):
    try:
        return ad.find_element(by, value).text.strip()
    except NoSuchElementException:
        return None


def get_element_attr(ad, by, value, attr):
    try:
        return ad.find_element(by, value).get_attribute(attr)
    except NoSuchElementException:
        return None


def parse_listing(parse_driver, known_links):
    """
    Generator: checks and filters each listing right after it's parsed,
    instead of as a batch after the whole page is done. known_links is a
    shared set (previously saved urls + everything found this run),
    mutated in place here.
    """
    ads = parse_driver.find_elements(By.CLASS_NAME, "EntityList-item")
    for ad in ads:
        price = get_element_text(ad, By.CLASS_NAME, "price")
        link = get_element_attr(ad, By.TAG_NAME, "a", "href")

        if not link or not link.startswith("https://www.njuskalo.hr/nekretnine/") or link in known_links:
            continue

        known_links.add(link)
        yield {"price": price, "link": link}


def build_search_url(flags, page):
    return (
        f"https://www.njuskalo.hr/iznajmljivanje-stanova/zagreb?"
        f"price[min]={flags.min_price}&price[max]={flags.max_price}"
        f"&livingArea[min]={flags.min_square}&livingArea[max]={flags.max_square}"
        f"&page={page}"
    )


def fetch_page_data(driver, url, known_links, retry, on_retry=None):
    """
    driver is passed in explicitly — scraper.py shouldn't need to know
    where it comes from (Chrome/Firefox, headless or not, which binary) —
    that's main.py's responsibility.
    """
    driver.get(url)
    data = list(parse_listing(driver, known_links))

    if not data and retry:
        if on_retry:
            on_retry()
        time.sleep(2)
        driver.get(url)
        data = list(parse_listing(driver, known_links))

    return data


class EmptyPageTracker:
    def __init__(self, limit=2):
        self.limit = limit
        self.count = 0

    def record(self, new_ads_count):
        if new_ads_count == 0:
            self.count += 1
        else:
            self.count = 0
        return self.count >= self.limit


def collect_data(driver, pages, flags, retry=False, on_new_ads=None):
    """MAIN ENTRY POINT — called from main.py, driver is passed in explicitly."""
    all_data = []
    total_ads = 0
    known_links = storage.load_previous_data()
    empty_tracker = EmptyPageTracker(limit=2)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=_console,
        transient=True,
    ) as progress:
        task = progress.add_task("[dim]Starting...[/dim]", total=None)

        for page in range(1, pages):
            progress.update(task, description=f"[dim]Scraping page {page}...[/dim]")

            url = build_search_url(flags, page)
            new_ads = fetch_page_data(
                driver,
                url,
                known_links,
                retry,
                on_retry=lambda: progress.update(
                    task, description=f"[dim]Page {page} empty, retrying...[/dim]"
                ),
            )

            if new_ads:
                storage.save_listings(new_ads)
                if on_new_ads:
                    on_new_ads(new_ads)

            all_data.extend(new_ads)
            total_ads += len(new_ads)

            _console.print(f"  Page [bold]{page}[/bold]  [green]+{len(new_ads)}[/green] new")

            if empty_tracker.record(len(new_ads)):
                break

    return all_data, total_ads