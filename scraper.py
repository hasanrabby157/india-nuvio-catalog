import json
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://ottweek.com"

LANGUAGES = {
    "hindi": {
        "name": "Hindi",
        "code": "HI",
    },
    "tamil": {
        "name": "Tamil",
        "code": "TA",
    },
    "telugu": {
        "name": "Telugu",
        "code": "TE",
    },
    "malayalam": {
        "name": "Malayalam",
        "code": "ML",
    },
    "bengali": {
        "name": "Bengali",
        "code": "BN",
    },
}


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 12; "
        "M2003J15SC) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0 Mobile Safari/537.36"
    )
}


session = requests.Session()
session.headers.update(HEADERS)


def clean(text):
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


def get(url):
    response = session.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    return response.text


# =========================================================
# NEW RELEASES
# =========================================================

def parse_new_releases(html, language):

    soup = BeautifulSoup(html, "html.parser")

    items = []
    inside = False

    for element in soup.find_all(["h2", "h3"]):

        text = clean(
            element.get_text(" ", strip=True)
        )

        lower = text.lower()

        # Start actual release section
        if (
            element.name == "h2"
            and "new" in lower
            and "releases on ott" in lower
        ):
            inside = True
            continue

        if not inside:
            continue

        # Stop when release section ends
        stop_words = [
            "by platform",
            "more languages",
            "trending",
            "what's new",
            "guides & original writing",
        ]

        if any(
            word in lower
            for word in stop_words
        ):
            break

        if element.name != "h3":
            continue

        title = text

        if not title:
            continue

        # Find card
        card = element

        for _ in range(6):

            if card.parent:
                card = card.parent

            card_text = clean(
                card.get_text(" ", strip=True)
            )

            if re.search(
                r"\b(Movie|Series)\b",
                card_text,
                re.I
            ):
                break

        card_text = clean(
            card.get_text(" ", strip=True)
        )

        # Type
        if re.search(
            r"\bSeries\b",
            card_text,
            re.I
        ):
            item_type = "series"

        elif re.search(
            r"\bMovie\b",
            card_text,
            re.I
        ):
            item_type = "movie"

        else:
            continue

        # Date
        date_match = re.search(
            r"\b("
            r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
            r")\s+\d{1,2}"
            r"(?:,\s+\d{4})?",
            card_text,
            re.I
        )

        release_date = (
            date_match.group(0)
            if date_match
            else None
        )

        # URL
        title_url = None

        for link in card.find_all(
            "a",
            href=True
        ):

            href = link["href"]

            if not href.startswith("/"):
                continue

            if "/title/" in href:

                title_url = urljoin(
                    BASE_URL,
                    href
                )

                break

        item = {
            "title": title,
            "type": item_type,
            "language": language,
            "release_date": release_date,
            "url": title_url,
        }

        # Remove duplicates
        duplicate = any(
            old["title"].lower()
            == title.lower()
            and old["type"]
            == item_type
            for old in items
        )

        if not duplicate:
            items.append(item)

    return items


def get_new_releases():

    result = {}

    for slug, info in LANGUAGES.items():

        print()
        print(
            f"Fetching {info['name']} releases..."
        )

        url = (
            f"{BASE_URL}/language/{slug}"
        )

        try:

            html = get(url)

            items = parse_new_releases(
                html,
                info["name"]
            )

            result[slug] = items

            print(
                f"{info['name']}: "
                f"{len(items)} releases"
            )

        except Exception as error:

            print(
                f"ERROR {info['name']}: "
                f"{error}"
            )

            result[slug] = []

    return result


# =========================================================
# TRENDING DEBUG
# =========================================================

def get_trending():

    print()
    print("=" * 60)
    print("FETCHING TRENDING DEBUG")
    print("=" * 60)

    html = get(BASE_URL)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Find every text node containing "Trending now"
    matches = soup.find_all(
        string=re.compile(
            r"trending now",
            re.I
        )
    )

    print()
    print(
        f"Found {len(matches)} "
        f"'Trending now' text matches"
    )

    for index, match in enumerate(
        matches[:10],
        start=1
    ):

        parent = match.parent

        print()
        print(
            f"--------------- MATCH {index} ---------------"
        )

        print(
            "TAG:",
            parent.name
        )

        print(
            "CLASS:",
            parent.get("class")
        )

        print(
            "ID:",
            parent.get("id")
        )

        print()
        print("TEXT:")

        print(
            clean(
                parent.get_text(
                    " ",
                    strip=True
                )
            )[:1000]
        )

        print()
        print("HTML:")

        print(
            str(parent)[:4000]
        )

        # Show nearby links
        print()
        print("NEARBY LINKS:")

        links = parent.find_all(
            "a",
            href=True
        )

        for link in links[:20]:

            print(
                " -",
                clean(
                    link.get_text(
                        " ",
                        strip=True
                    )
                ),
                "|",
                link.get("href")
            )

    print()
    print("=" * 60)
    print("END TRENDING DEBUG")
    print("=" * 60)

    # We intentionally return empty for now.
    # Once we see the real HTML structure,
    # we will replace this with the final parser.
    return []


# =========================================================
# BUILD CATALOGUE
# =========================================================

def build
