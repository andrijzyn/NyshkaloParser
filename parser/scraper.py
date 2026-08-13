"""Page scraping logic for njuskalo.hr apartment listings."""
import time
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from rich.progress import Progress, SpinnerColumn, TextColumn


def get_element_text(ad, by, value):
    """Return the stripped text of a child element, or None if it's missing."""
    try:
        return ad.find_element(by, value).text.strip()
    except NoSuchElementException:
        return None


def get_element_attr(ad, by, value, attr):
    """Return an attribute of a child element, or None if it's missing."""
    try:
        return ad.find_element(by, value).get_attribute(attr)
    except NoSuchElementException:
        return None


def parse_listing(parse_driver, known_links, settings, console):
    """
    Generator: checks and filters each listing right after it's parsed,
    instead of as a batch after the whole page is done. known_links is a
    shared set (previously saved urls + everything found this run),
    mutated in place here. console must be the same Console instance driving
    the active Progress/Live display (see collect_data) — printing through a
    second, unrelated Console while a Live display is active desyncs the
    terminal cursor and garbles output.
    """
    site = settings.site
    ads = parse_driver.find_elements(By.CLASS_NAME, site.listing_class)
    for ad in ads:
        price = get_element_text(ad, By.CLASS_NAME, site.price_class)
        link = get_element_attr(ad, By.TAG_NAME, "a", "href")
        is_listing_link = link and link.startswith(site.listing_link_prefix)

        if not is_listing_link:
            continue

        if link in known_links:
            console.print(f"    [dim]Passed[/dim]  [cyan]{link}[/cyan]")
            continue

        known_links.add(link)
        yield {"price": price, "link": link}


def build_search_url(flags, page, settings):
    """Build the search URL for a given page and filter flags."""
    site = settings.site
    return (
        f"{site.base_url}/iznajmljivanje-stanova/{site.city}?"
        f"price[min]={flags.min_price}&price[max]={flags.max_price}"
        f"&livingArea[min]={flags.min_square}&livingArea[max]={flags.max_square}"
        f"&page={page}"
    )


def fetch_page_data(driver, url, known_links, retry, settings, console, on_retry=None):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """
    driver is passed in explicitly — scraper.py shouldn't need to know
    where it comes from (Chrome/Firefox, headless or not, which binary) —
    that's main.py's responsibility.
    """
    driver.get(url)
    data = list(parse_listing(driver, known_links, settings, console))

    if not data and retry:
        if on_retry:
            on_retry()
        time.sleep(settings.scraping.retry_sleep_seconds)
        driver.get(url)
        data = list(parse_listing(driver, known_links, settings, console))

    return data


class EmptyPageTracker:  # pylint: disable=too-few-public-methods
    """Tracks consecutive pages with no new ads, to know when to stop scraping."""

    def __init__(self, limit):
        self.limit = limit
        self.count = 0

    def record(self, new_ads_count):
        """Record a page's new-ad count; return True once the limit is reached."""
        if new_ads_count == 0:
            self.count += 1
        else:
            self.count = 0
        return self.count >= self.limit


def collect_data(driver, storage, flags, settings, console, retry=False, on_new_ads=None):  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    """
    MAIN ENTRY POINT — called from main.py, driver and storage are passed in explicitly.
    console must be the same Console instance main.py uses everywhere else (including
    inside on_new_ads) — Progress/Live only knows how to coordinate redraws for output
    going through the exact console it was built with; a second Console() writing to the
    same terminal desyncs the cursor and garbles the spinner output.
    """
    all_data = []
    total_ads = 0
    known_links = storage.load_previous_data()
    empty_tracker = EmptyPageTracker(limit=settings.scraping.empty_page_limit)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("[dim]Starting...[/dim]", total=None)

        for page in range(1, flags.pages):
            progress.update(task, description=f"[dim]Scraping page {page}...[/dim]")

            url = build_search_url(flags, page, settings)
            new_ads = fetch_page_data(
                driver,
                url,
                known_links,
                retry,
                settings,
                console,
                on_retry=lambda p=page: progress.update(
                    task, description=f"[dim]Page {p} empty, retrying...[/dim]"
                ),
            )

            if new_ads:
                storage.save_listings(new_ads)
                if on_new_ads:
                    on_new_ads(new_ads)

            all_data.extend(new_ads)
            total_ads += len(new_ads)

            console.print(f"  Page [bold]{page}[/bold]  [green]+{len(new_ads)}[/green] new")

            if empty_tracker.record(len(new_ads)):
                break

    return all_data, total_ads
