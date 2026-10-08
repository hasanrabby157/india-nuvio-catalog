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


# =========================================================
# HELPERS
# =========================================================

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

        # -------------------------------------------------
        # Start of New Releases section
        # -------------------------------------------------

        if (
            element.name == "h2"
            and "new" in lower
            and "releases on ott" in lower
        ):

            inside = True
            continue

        if not inside:
            continue

        # -------------------------------------------------
        # End of section
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Find card
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Detect type
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Detect release date
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Find title URL
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Create item
        # -------------------------------------------------

        item = {
            "title": title,
            "type": item_type,
            "language": language,
            "release_date": release_date,
            "url": title_url,
        }

        # -------------------------------------------------
        # Avoid duplicates
        # -------------------------------------------------

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
    # Next.js serialized data
    # -----------------------------------------------------

    patterns = [

        r'pathname\\?"\s*:\s*\\?"'
        r'(/title/(?:movie|tv)/[^"\\]+)',

        r'"pathname"\s*:\s*'
        r'"(/title/(?:movie|tv)/[^"]+)',

        r'pathname"\s*:\s*'
        r'"(/title/(?:movie|tv)/[^"]+)',
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

    # Only Top 20
    return links[:20]


def get_trending(releases):

    print()
    print("=" * 60)
    print("FETCHING TRENDING")
    print("=" * 60)

    # -----------------------------------------------------
    # Fetch homepage only
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Build release lookup
    #
    # We use the already downloaded language pages.
    # No title-page requests.
    # -----------------------------------------------------

    release_lookup = {}

    for language_items in releases.values():

        for item in language_items:

            url = item.get(
                "url"
            )

            if not url:
                continue

            normalized = (
                url
                .rstrip("/")
                .lower()
            )

            release_lookup[
                normalized
            ] = item

    trending = []

    # -----------------------------------------------------
    # Process Trending Top 20
    # -----------------------------------------------------

    for position, href in enumerate(
        links,
        start=1
    ):

        url = urljoin(
            BASE_URL,
            href
        )

        # -------------------------------------------------
        # Detect type
        # -------------------------------------------------

        if "/title/movie/" in href:

            item_type = "movie"

        elif "/title/tv/" in href:

            item_type = "series"

        else:

            continue

        # -------------------------------------------------
        # Try exact URL match
        # -------------------------------------------------

        normalized = (
            url
            .rstrip("/")
            .lower()
        )

        matched = release_lookup.get(
            normalized
        )

        if matched:

            title = matched["title"]
            language = matched["language"]

        else:

            # -------------------------------------------------
            # Try title slug matching
            # -------------------------------------------------

            slug = (
                href
                .rstrip("/")
                .split("/")[-1]
            )

            slug = re.sub(
                r"^\d+-",
                "",
                slug
            )

            slug_title = clean(
                slug.replace(
                    "-",
                    " "
                )
            ).lower()

            matched = None

            for language_items in releases.values():

                for item in language_items:

                    item_title = clean(
                        item["title"]
                    ).lower()

                    if (
                        item["type"]
                        == item_type
                        and item_title
                        == slug_title
                    ):

                        matched = item
                        break

                if matched:
                    break

            if matched:

                title = matched["title"]
                language = matched["language"]

            else:

                # -------------------------------------------------
                # Unknown language
                # -------------------------------------------------

                title = slug_title.title()
                language = None

        # -------------------------------------------------
        # Print result
        # -------------------------------------------------

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

        if language:

            print(
                "Language: "
                + language
            )

            trending.append({

                "title": title,

                "type": item_type,

                "language": language,

                "url": url,

                "rank": position,
            })

        else:

            print(
                "Language: UNKNOWN "
                "(not in current releases)"
            )

    print()
    print(
        "Trending with known language: "
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

        # -------------------------------------------------
        # New Movies
        # -------------------------------------------------

        new_movies = []

        # -------------------------------------------------
        # New Series
        # -------------------------------------------------

        new_series = []

        for item in language_releases:

            if item["type"] == "movie":

                new_movies.append(
                    item
                )

            elif item["type"] == "series":

                new_series.append(
                    item
                )

        # -------------------------------------------------
        # Language-specific Trending
        # -------------------------------------------------

        language_trending = []

        for item in trending:

            if (
                item.get("language")
                == language_name
            ):

                language_trending.append(
                    item
                )

        # -------------------------------------------------
        # Trending Movies
        # -------------------------------------------------

        trending_movies = []

        # -------------------------------------------------
        # Trending Series
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Final language section
        # -------------------------------------------------

        catalogue[slug] = {

            "language":
                language_name,

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

    # -----------------------------------------------------
    # Get New Releases
    # -----------------------------------------------------

    releases = get_new_releases()

    # -----------------------------------------------------
    # Get Trending
    # IMPORTANT:
    # Pass releases so Trending does not need title-page
    # requests.
    # -----------------------------------------------------

    trending = get_trending(
        releases
    )

    # -----------------------------------------------------
    # Build Catalogue
    # -----------------------------------------------------

    catalogue = build_catalogue(
        releases,
        trending
    )

    # -----------------------------------------------------
    # Save catalogue.json
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Save trending.json
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Final Result
    # -----------------------------------------------------

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
        print(
            "Trending titles:"
        )

        for item in data["trending"]:

            print(
                "- "
                + item["title"]
                + " | "
                + item["type"]
                + " | "
                + item["language"]
            )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
