That was an interesting task during the hardest period of my life.
I did not like look for an apartments which suit under my budget and prioritized location.
And also because the internal "Njuškalo" filters are garbage.

I mainly used Selenium, a library for automated website testing.
It closes all anti-bot windows and scrapes data from the advertisement divs.
That was a problem for me because it's a bit broken in "Njuškalo".

Additional Python libraries clean the data from other advertisements.
Listings are stored in a PostgreSQL database, de-duplicated by URL as each one is parsed.

<img width="850" height="500" alt="graph" src="https://github.com/user-attachments/assets/c8bdce20-e71c-44ed-934b-b235ca6ed055" />

<img width="850" height="500" alt="diffs" src="https://github.com/user-attachments/assets/dc3aaa61-881c-4a74-b586-2c47e6a3d9c1" />

<img width="850" height="500" alt="CLI table" src="https://github.com/user-attachments/assets/3e02a85f-e5bd-47c2-a111-e9db2ec27caa" />

<img width="1891" height="1014" alt="DBeaver PostgreSQL table" src="https://github.com/user-attachments/assets/dfbea02c-cdd5-4a9b-b3e5-051e8464ebf7" />



---

## Setup

```bash
pip install -r requirements.txt
```

Requires a running PostgreSQL server. Create the database (the `listings` table is created automatically on first run):

```bash
createdb flats
```

Configure search parameters and the database connection in `config.toml`:

```toml
[parser]
min_price = 200   # minimum rent (€)
max_price = 400   # maximum rent (€)
max_square = 45   # maximum area (m²)
min_square = 36   # minimum area (m²)

[directories]
save = "data"     # output folder

[database]
dbname = "flats"
user = "admin"    # must have access to connect + create/use the listings table
```

The connection relies on local trust/peer authentication (unix socket, no password). For a remote/password-protected server, set standard `PGHOST`/`PGPASSWORD` environment variables — `psycopg` picks them up automatically.

## Usage

```bash
python main.py [options]
```

| Flag | Description |
|---|---|
| `--pages N` | Scrape up to N pages (default: 100) |
| `--min-price N` | Override minimum price from config |
| `--max-price N` | Override maximum price from config |
| `--min-square N` | Override minimum area from config |
| `--max-square N` | Override maximum area from config |
| `--clean` | Delete all previous listings from the database before running |
| `--graph` | Show price distribution chart in terminal |
| `--iter` | Retry empty pages before skipping |

## Examples

```bash
# Basic run
python main.py

# Quick scan of first 5 pages with a wider budget
python main.py --pages 5 --max-price 500

# Full re-scrape from scratch with chart
python main.py --clean --graph
```

## Output

Listings are saved to the `listings` table in PostgreSQL as each page is scraped — every link is checked against previously seen URLs (in the database and earlier in the same run) immediately after parsing, and only new ones are inserted. Prices are stored as integers (parsed from the raw "300 €" text). A summary table prints in the terminal at the end of each run.

The script stops automatically when it finds no new listings across 2 consecutive pages.
