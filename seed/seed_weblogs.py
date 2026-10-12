"""Writes a made-up web server log in Apache "combined" format.

Run from the project folder (after seed_postgres):   python -m seed.seed_weblogs

One line looks like this:
181.20.3.44 - user007 [10/Oct/2025:13:55:36 -0300] "GET /catalog HTTP/1.1" 200 5123 "-" "Mozilla/5.0 (...)"

The log is made of visits: a user logs in and opens 1 to 6 pages within a few minutes, from the same
device and address. Each page is one line. The warehouse later counts one visit as one login.

Some lines are wrong on purpose: every 100th line is cut off, and every 50th visit uses a username
that does not exist.
"""

import csv
import random
from datetime import timedelta

from sources.postgres.connection import CONFIG, LOG_FILE, ROOT, connect_source, local_now

SIZES = CONFIG["seed"]
random.seed(SIZES["random_seed"])

PAGES = ["/", "/catalog", "/cart", "/orders", "/account"]

# The browser text each kind of device sends, and how common it is.
USER_AGENTS = {
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36": 40,
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36": 20,
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1": 15,
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15": 12,
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36": 6,
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1": 4,
    "Mozilla/5.0 (Linux; Android 13; SM-X700) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36": 2,
    "curl/8.4.0": 1,
}


def main():
    # The usernames that really exist, with the country of their company.
    with connect_source() as source:
        users = source.execute(
            "SELECT u.username, c.country_code FROM b2b.users u JOIN b2b.companies c USING (company_id)"
        ).fetchall()

    # country -> the IP prefixes that belong to it, e.g. {"AR": ["181", "186", "190"], ...}
    prefixes_of_country = {}
    with open(ROOT / CONFIG["ip_country_file"]) as csv_file:
        for row in csv.DictReader(csv_file):
            prefixes_of_country.setdefault(row["country_code"], []).append(row["ip_prefix"])

    end = local_now() - timedelta(days=1)
    history_seconds = SIZES["months_of_history"] * 30 * 24 * 3600

    # Build every visit; each one gives a few (time, text) log lines.
    lines = []
    for visit_number in range(1, SIZES["logins"] + 1):
        username, country = random.choice(users)
        if random.random() < 0.10:
            country = random.choice(list(prefixes_of_country))  # logging in while travelling
        first_part = random.choice(prefixes_of_country[country])
        if random.random() < 0.01:
            first_part = "8"  # an address that is not in the country file
        ip = f"{first_part}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        user_agent = random.choices(list(USER_AGENTS), list(USER_AGENTS.values()))[0]

        if random.random() < 0.10:
            username = "-"  # a visitor who is not logged in
        if visit_number % 50 == 0:
            username = "ghost_user"  # bad data: this username does not exist

        page_time = end - timedelta(seconds=random.randint(0, history_seconds))
        for _ in range(random.randint(1, 6)):
            stamp = page_time.strftime("%d/%b/%Y:%H:%M:%S %z")
            page = random.choice(PAGES)
            size = random.randint(200, 9000)
            lines.append((page_time, f'{ip} - {username} [{stamp}] "GET {page} HTTP/1.1" 200 {size} "-" "{user_agent}"'))
            page_time += timedelta(seconds=random.randint(10, 300))  # the next page, a little later

    # A real log is written in time order.
    lines.sort()
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w") as log_file:
        for line_number, (_, line) in enumerate(lines, start=1):
            if line_number % 100 == 0:
                line = line[:40]  # bad data: the line is cut off
            log_file.write(line + "\n")

    print(f"Wrote {len(lines)} lines ({SIZES['logins']} visits) to {LOG_FILE}")


if __name__ == "__main__":
    main()
