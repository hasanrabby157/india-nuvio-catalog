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


# --------------------------------------------------
# NEW RELEASES
# --------------------------------------------------

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

        # Stop at next section
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


# --------------------------------------------------
# TRENDING
# --------------------------------------------------

def get_trending():

    print()
    print("Fetching Trending...")

    html = get(BASE_URL)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    trending = []

    trending_heading = None

    # Find "Trending now"
    for heading in soup.find_all(
        ["h2", "h3"]
    ):

        text = clean(
            heading.get_text(
                " ",
                strip=True
            )
        ).lower()

        if text == "trending now":

            trending_heading = heading
            break

    if not trending_heading:

        print("Trending section not found")

        return []

    # Find links after Trending heading
    for link in trending_heading.find_all_next(
        "a",
        href=True
    ):

        href = link["href"]

        # Only actual title pages
        if "/title/" not in href:
            continue

        raw_text = clean(
            link.get_text(
                " ",
                strip=True
            )
        )

        if not raw_text:
            continue

        # Remove ranking number
        text = re.sub(
            r"^\d+",
            "",
            raw_text
        ).strip()

        # Remove status prefixes
        text = re.sub(
            r"^(All week|Trending|Rising fast|On the rise)\s+",
            "",
            text,
            flags=re.I
        )

        # Remove Day X suffix
        text = re.sub(
            r"\s+Day\s+\d+$",
            "",
            text,
            flags=re.I
        ).strip()

        if not text:
            continue

        full_url = urljoin(
            BASE_URL,
            href
        )

        # Prevent duplicates
        if any(
            item["url"] == full_url
            for item in trending
        ):
            continue

        trending.append({
            "title": text,
            "url": full_url,
            "type": None,
            "language_code": None,
            "language": None,
        })

        # We only need top 10
        if len(trending) >= 10:
            break

    print(
        f"Found {len(trending)} trending titles"
    )

    return trending


# --------------------------------------------------
# TRENDING TITLE DETAILS
# --------------------------------------------------

def get_title_details(item):

    try:

        html = get(
            item["url"]
        )

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # Determine Movie / Series
        page_text = clean(
            soup.get_text(
                " ",
                strip=True
            )
        )

        # First metadata line near title
        item_type = None

        if re.search(
            r"\bSeries\b",
            page_text[:5000],
            re.I
        ):
            item_type = "series"

        elif re.search(
            r"\bMovie\b",
            page_text[:5000],
            re.I
        ):
            item_type = "movie"

        # Language
        language_code = None

        language_match = re.search(
            r"\bLanguage\s+([A-Z]{2})\b",
            page_text,
            re.I
        )

        if language_match:

            language_code = (
                language_match
                .group(1)
                .upper()
            )

        # Map language code
        language_name = None

        for slug, info in LANGUAGES.items():

            if (
                language_code
                == info["code"]
            ):
                language_name = (
                    info["name"]
                )
                break

        item["type"] = item_type
        item["language_code"] = language_code
        item["language"] = language_name

        return item

    except Exception as error:

        print(
            f"Could not read "
            f"{item['title']}: {error}"
        )

        return item


def enrich_trending(trending):

    result = []

    for index, item in enumerate(
        trending,
        start=1
    ):

        print(
            f"Trending {index}/"
            f"{len(trending)}: "
            f"{item['title']}"
        )

        item = get_title_details(
            item
        )

        result.append(item)

        # Don't hammer the site
        time.sleep(0.5)

    return result


# --------------------------------------------------
# BUILD CATALOGUE
# --------------------------------------------------

def build_catalogue(
    releases,
    trending
):

    catalogue = {}

    for slug, info in LANGUAGES.items():

        language_name = info["name"]

        language_releases = (
            releases.get(
                slug,
                []
            )
        )

        # New releases
        new_movies = [
            item
            for item in language_releases
            if item["type"] == "movie"
        ]

        new_series = [
            item
            for item in language_releases
            if item["type"] == "series"
        ]

        # Trending for this language
        language_trending = [
            item
            for item in trending
            if item["language"]
            == language_name
        ]

        trending_movies = [
            item
            for item in language_trending
            if item["type"] == "movie"
        ]

        trending_series = [
            item
            for item in language_trending
            if item["type"] == "series"
        ]

        catalogue[slug] = {

            "language": language_name,

            "new_releases":
                language_releases,

            "new_movies":
                new_movies,

            "new_series":
                new_series,

            "trending":
                language_trending,

            "trending_movies":
                trending_movies,

            "trending_series":
                trending_series,
        }

    return catalogue


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print()
    print("=" * 60)
    print("OTTweek India Catalogue Scraper")
    print("=" * 60)

    # 1. New releases
    releases = get_new_releases()

    # 2. Trending
    trending = get_trending()

    # 3. Get language/type of each trending title
    trending = enrich_trending(
        trending
    )

    # 4. Build final catalogue
    catalogue = build_catalogue(
        releases,
        trending
    )

    # Save full catalogue
    with open(
        "catalogue.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            catalogue,
            file,
            ensure_ascii=False,
            indent=2
        )

    # Save trending separately for debugging
    with open(
        "trending.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            trending,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 60)
    print("FINAL RESULT")
    print("=" * 60)

    for slug, data in catalogue.items():

        print()
        print(
            f"{data['language']}"
        )

        print(
            f"  New Releases: "
            f"{len(data['new_releases'])}"
        )

        print(
            f"  New Movies: "
            f"{len(data['new_movies'])}"
        )

        print(
            f"  New Series: "
            f"{len(data['new_series'])}"
        )

        print(
            f"  Trending: "
            f"{len(data['trending'])}"
        )

        print(
            f"  Trending Movies: "
            f"{len(data['trending_movies'])}"
        )

        print(
            f"  Trending Series: "
            f"{len(data['trending_series'])}"
        )

    print()
    print(
        "Saved catalogue.json"
    )

    print(
        "Saved trending.json"
    )


if __name__ == "__main__":
    main()
