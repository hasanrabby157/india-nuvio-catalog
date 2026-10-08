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


CODE_TO_LANGUAGE = {
    "HI": "Hindi",
    "TA": "Tamil",
    "TE": "Telugu",
    "ML": "Malayalam",
    "BN": "Bengali",
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


# =========================================================
# HELPERS
# =========================================================

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

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    items = []

    inside = False

    for element in soup.find_all(["h2", "h3"]):

        text = clean(
            element.get_text(
                " ",
                strip=True
            )
        )

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

        for link in card.find_all(
            "a",
            href=True
        ):

            href = link.get(
                "href",
                ""
            )

            if (
                href.startswith("/")
                and "/title/" in href
            ):
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

        duplicate = False

        for old in items:

            if (
                old["title"].lower()
                == title.lower()
                and old["type"]
                == item_type
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
        print(
            "Fetching "
            + info["name"]
            + " releases..."
        )

        url = (
            BASE_URL
            + "/language/"
            + slug
        )

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
                    + str(
                        item["release_date"]
                    )
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
# TRENDING
# =========================================================

def extract_trending_links(html):

    links = []

    # -----------------------------------------------------
    # Method 1:
    # Look for Next.js pathname data
    # -----------------------------------------------------

    patterns = [
        r'pathname\\?"\s*:\s*\\?"(/title/(?:movie|tv)/[^"\\]+)',
        r'"pathname"\s*:\s*"(/title/(?:movie|tv)/[^"]+)',
        r'pathname"\s*:\s*"(/title/(?:movie|tv)/[^"]+)',
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            html,
            re.I
        )

        for href in matches:

            href = href.replace(
                "\\/",
                "/"
            )

            href = href.replace(
                "\\u0026",
                "&"
            )

            if href not in links:

                links.append(href)

    # -----------------------------------------------------
    # Method 2:
    # Normal HTML links
    # -----------------------------------------------------

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link.get(
            "href",
            ""
        )

        if (
            href.startswith(
                "/title/movie/"
            )
            or href.startswith(
                "/title/tv/"
            )
        ):

            if href not in links:
                links.append(href)

    return links[:20]


def get_title_from_url(url):

    last_part = url.rstrip(
        "/"
    ).split("/")[-1]

    # Remove TMDB/OTTweek numeric ID
    last_part = re.sub(
        r"^\d+-",
        "",
        last_part
    )

    # Convert slug to title
    title = last_part.replace(
        "-",
        " "
    )

    return title.strip()


def detect_language_from_page(
    html,
    expected_type
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = clean(
        soup.get_text(
            " ",
            strip=True
        )
    )

    # -----------------------------------------------------
    # Look for "Language HI"
    # -----------------------------------------------------

    patterns = [
        r"\bLanguage\s*:?\s*([A-Z]{2})\b",
        r'"language"\s*:\s*"([A-Z]{2})"',
        r'"originalLanguage"\s*:\s*"([A-Z]{2})"',
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            html,
            re.I
        )

        for code in matches:

            code = code.upper()

            if code in CODE_TO_LANGUAGE:
                return CODE_TO_LANGUAGE[code]

    # Try visible page text
    matches = re.findall(
        r"\bLanguage\s*:?\s*([A-Za-z]{2})\b",
        text,
        re.I
    )

    for code in matches:

        code = code.upper()

        if code in CODE_TO_LANGUAGE:
            return CODE_TO_LANGUAGE[code]

    return None


def parse_trending_item(
    href,
    position
):

    url = urljoin(
        BASE_URL,
        href
    )

    if "/title/movie/" in href:
        item_type = "movie"

    elif "/title/tv/" in href:
        item_type = "series"

    else:
        return None

    title = get_title_from_url(
        href
    )

    print()
    print(
        "Trending "
        + str(position)
        + ": "
        + title
    )

    print(
        "Type: "
        + item_type
    )

    try:

        html = get(url)

        language = detect_language_from_page(
            html,
            item_type
        )

        if language:

            print(
                "Language: "
                + language
            )

        else:

            print(
                "Language: UNKNOWN"
            )

        if not language:
            return None

        return {
            "title": title,
            "type": item_type,
            "language": language,
            "url": url,
            "rank": position,
        }

    except Exception as error:

        print(
            "ERROR loading title: "
            + str(error)
        )

        return None


def get_trending():

    print()
    print("=" * 60)
    print("FETCHING TRENDING")
    print("=" * 60)

    html = get(
        BASE_URL
    )

    links = extract_trending_links(
        html
    )

    print()
    print(
        "Trending links found: "
        + str(len(links))
    )

    trending = []

    for position, href in enumerate(
        links,
        start=1
    ):

        item = parse_trending_item(
            href,
            position
        )

        if item:
            trending.append(item)

    print()
    print(
        "Successfully parsed trending: "
        + str(len(trending))
    )

    return trending


# =========================================================
# BUILD CATALOGUE
# =========================================================

def build_catalogue(
    releases,
    trending
):

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

            if (
                item.get("language")
                == language_name
            ):
                language_trending.append(
                    item
                )

        trending_movies = []
        trending_series = []

        for item in language_trending:

            if item.get("type") == "movie":
                trending_movies.append(
                    item
                )

            elif item.get("type") == "series":
                trending_series.append(
                    item
                )

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


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 60)
    print("OTTweek India Catalogue Scraper")
    print("=" * 60)

    # Get new releases
    releases = get_new_releases()

    # Get trending
    trending = get_trending()

    # Build catalogue
    catalogue = build_catalogue(
        releases,
        trending
    )

    # Save catalogue
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

    # Save trending
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

    # Final result
    print()
    print("=" * 60)
    print("FINAL RESULT")
    print("=" * 60)

    for slug, data in catalogue.items():

        print()
        print(
            data["language"].upper()
        )

        print(
            "New Releases: "
            + str(
                len(
                    data["new_releases"]
                )
            )
        )

        print(
            "New Movies: "
            + str(
                len(
                    data["new_movies"]
                )
            )
        )

        print(
            "New Series: "
            + str(
                len(
                    data["new_series"]
                )
            )
        )

        print(
            "Trending: "
            + str(
                len(
                    data["trending"]
                )
            )
        )

        print(
            "Trending Movies: "
            + str(
                len(
                    data["trending_movies"]
                )
            )
        )

        print(
            "Trending Series: "
            + str(
                len(
                    data["trending_series"]
                )
            )
        )

        print()
        print("Trending titles:")

        for item in data["trending"]:

            print(
                "- "
                + item["title"]
                + " | "
                + item["type"]
                + " | "
                + item["language"]
            )


if __name__ == "__main__":
    main()
