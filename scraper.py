import json
import re
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

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


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

def parse_new_releases(
    html,
    language
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    items = []

    inside = False

    for element in soup.find_all(
        ["h2", "h3"]
    ):

        text = clean(
            element.get_text(
                " ",
                strip=True
            )
        )

        lower = text.lower()

        # Start of actual release section
        if (
            element.name == "h2"
            and "new" in lower
            and "releases on ott" in lower
        ):
            inside = True
            continue

        if not inside:
            continue

        # Stop at the next major section
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

        # Find the release card
        card = element

        for _ in range(6):

            if card.parent:
                card = card.parent

            card_text = clean(
                card.get_text(
                    " ",
                    strip=True
                )
            )

            if re.search(
                r"\b(Movie|Series)\b",
                card_text,
                re.I
            ):
                break

        card_text = clean(
            card.get_text(
                " ",
                strip=True
            )
        )

        # Determine type
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

        # Find release date
        date_match = re.search(
            r"\b("
            r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
            r")\s+\d{1,2}"
            r"(?:,\s+\d{4})?",
            card_text,
            re.I
        )

        if date_match:
            release_date = date_match.group(0)
        else:
            release_date = None

        # Find title URL
        title_url = None

        for link in card.find_all(
            "a",
            href=True
        ):

            href = link.get("href", "")

            if (
                href.startswith("/")
                and "/title/" in href
            ):

                title_url =
