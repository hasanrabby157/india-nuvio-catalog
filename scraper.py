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

    return re.sub(r"\s+", " ", text).strip()


def get(url):
    response = session.get(url, timeout=30)
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

        text = clean(element.get_text(" ", strip=True))
        lower = text.lower()

        if (
            element.name == "h2"
            and "new" in lower
            and "releases on ott" in lower
        ):
            inside = True
            continue

        if not inside:
            continue

        stop_words = [
            "by platform",
            "more languages",
            "trending",
            "what's new",
            "guides & original writing",
        ]

        if any(word in lower for word in stop_words):
            break

        if element.name != "h3":
            continue

        title = text

        if not title:
            continue

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

        if re.search(r"\bSeries\b", card_text, re.I):
            item_type = "series"

        elif re.search(r"\bMovie\b", card_text, re.I):
            item_type = "movie"

        else:
            continue

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

        title_url = None

        for link in card.find_all("a", href=True):

            href = link.get("href", "")

            if (
                href.startswith("/")
                and "/title/" in href
            ):
                title_url = urljoin(BASE_URL, href)
                break

        item = {
            "title": title,
            "type": item_type,
            "language": language,
            "release_date": release_date,
            "url": title_url,
        }

        duplicate = False

        for old in items:

            if (
                old["title"].lower() == title.lower()
                and old["type"] == item_type
            ):
                duplicate = True
                break

        if not duplicate:
            items.append(item)

    return items


def get_new_releases():

    result = {}

    for slug, info in LANGUAGES.items():

        print()
        print("Fetching " + info["name"] + " releases...")

        url = BASE_URL + "/language/" + slug

        try:

            html = get(url)

            items = parse_new_releases(
                html,
                info["name"]
            )

            result[slug] = items

            print(
                info["name"]
                + ": "
                + str(len(items))
                + " releases"
            )

            for item in items[:10]:

                print(
                    item["title"]
                    + " | "
                    + item["type"]
                    + " | "
                    + str(item["release_date"])
                )

        except Exception as error:

            print(
                "ERROR "
                + info["name"]
                + ": "
                + str(error)
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

    matches = soup.find_all(
        string=re.compile(
            r"trending",
            re.I
        )
    )

    print()
    print(
        "Found "
        + str(len(matches))
        + " trending text matches"
    )

    for index, match in enumerate(
        matches[:10],
        start=1
    ):

        parent = match.parent

        print()
        print(
            "--------------- MATCH "
            + str(index)
            + " ---------------"
        )

        print(
            "TAG: "
            + str(parent.name)
        )

        print(
            "CLASS: "
            + str(parent.get("class"))
        )

        print(
            "ID: "
            + str(parent.get("id"))
        )

        print()
        print("TEXT:")

        print(
            clean(
                parent.get_text(
                    " ",
                    strip=True
                )
            )[:1500]
        )

        print()
        print("HTML:")

        print(
            str(parent)[:4000]
        )

        print()
        print("LINKS:")

        links = parent.find_all(
            "a",
            href=True
        )

        if not links:

            print("No links found")

        else:

            for link in links[:20]:

                link_text = clean(
                    link.get_text(
                        " ",
                        strip=True
                    )
                )

                print(
                    "- "
                    + link_text
                    + " | "
                    + str(link.get("href"))
                )

    print()
    print("=" * 60)
    print("END TRENDING DEBUG")
    print("=" * 60)

    return []


# =========================================================
# BUILD CATALOGUE
# =========================================================

def build_catalogue(releases, trending):

    catalogue = {}

    for slug, info in LANGUAGES.items():

        language_name = info["name"]

        language_releases = releases.get(
            slug,
            []
        )

        new_movies = []
        new_series = []

        for item in language_releases:

            if item["type"] == "movie":
                new_movies.append(item)

            elif item["type"] == "series":
                new_series.append(item)

        language_trending = []

        for item in trending:

            if item.get("language") == language_name:
                language_trending.append(item)

        trending_movies = []
        trending_series = []

        for item in language_trending:

            if item.get("type") == "movie":
                trending_movies.append(item)

            elif item.get("type") == "series":
                trending_series.append(item)

        catalogue[slug] = {
            "language": language_name,
            "new_releases": language_releases,
            "new_movies": new_movies,
            "new_series": new_series,
            "trending": language_trending,
            "trending_movies": trending_movies,
            "trending_series": trending_series,
        }

    return catalogue


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 60)
    print("OTTweek India Catalogue Scraper")
    print("=" * 60)

    releases = get_new_releases()

    trending = get_trending()

    catalogue = build_catalogue(
        releases,
        trending
    )

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
        print(data["language"].upper())

        print(
            "New Releases: "
            + str(len(data["new_releases"]))
        )

        print(
            "New Movies: "
            + str(len(data["new_movies"]))
        )

        print(
            "New Series: "
            + str(len(data["new_series"]))
        )

        print(
            "Trending: "
            + str(len(data["trending"]))
        )

        print(
            "Trending Movies: "
            + str(len(data["trending_movies"]))
        )

        print(
            "Trending Series: "
            + str(len(data["trending_series"]))
        )


if __name__ == "__main__":
    main()
