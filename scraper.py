import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://ottweek.com"

LANGUAGES = {
    "hindi": "Hindi",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "malayalam": "Malayalam",
    "bengali": "Bengali",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 12; "
        "M2003J15SC) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0 Mobile Safari/537.36"
    )
}


def clean(text):
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


def get_page(language):
    url = f"{BASE_URL}/language/{language}"

    print(f"Fetching: {url}")

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.text


def parse_releases(html, language):
    soup = BeautifulSoup(html, "html.parser")

    items = []
    inside_release_section = False

    # Find the heading for the current-week release section
    for element in soup.find_all(["h2", "h3"]):

        text = clean(element.get_text(" ", strip=True))
        lower = text.lower()

        # Start of actual release section
        if (
            element.name == "h2"
            and "new" in lower
            and "releases on ott" in lower
        ):
            inside_release_section = True
            continue

        if not inside_release_section:
            continue

        # IMPORTANT:
        # Stop as soon as the actual release grid ends.
        stop_words = [
            "by platform",
            "more languages",
            "trending",
            "what's new",
            "guides & original writing",
        ]

        if any(word in lower for word in stop_words):
            break

        # Only h3 elements inside this section are titles
        if element.name != "h3":
            continue

        title = text

        if not title:
            continue

        # Find the card containing this title
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
                re.IGNORECASE
            ):
                break

        card_text = clean(
            card.get_text(" ", strip=True)
        )

        # Determine type
        item_type = None

        if re.search(r"\bSeries\b", card_text):
            item_type = "series"

        elif re.search(r"\bMovie\b", card_text):
            item_type = "movie"

        if not item_type:
            continue

        # Find release date
        date_match = re.search(
            r"\b("
            r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
            r")\s+\d{1,2}"
            r"(?:,\s+\d{4})?",
            card_text,
            re.IGNORECASE
        )

        release_date = (
            date_match.group(0)
            if date_match
            else None
        )

        # Find actual title URL
        title_url = None

        for link in card.find_all("a", href=True):

            href = link.get("href", "")

            if not href.startswith("/"):
                continue

            # Don't use navigation/filter links
            if any(
                x in href.lower()
                for x in [
                    "/language/",
                    "/platform/",
                    "/genre/",
                    "/type/",
                    "/week/",
                ]
            ):
                continue

            title_url = urljoin(
                BASE_URL,
                href
            )

            break

        item = {
            "title": title,
            "type": item_type,
            "language": LANGUAGES[language],
            "release_date": release_date,
            "url": title_url,
        }

        # Prevent duplicates
        duplicate = any(
            old["title"].lower() == title.lower()
            and old["type"] == item_type
            for old in items
        )

        if not duplicate:
            items.append(item)

    return items


def main():

    catalogue = {}

    for slug, language_name in LANGUAGES.items():

        print()
        print("=" * 50)
        print(language_name)
        print("=" * 50)

        try:

            html = get_page(slug)

            items = parse_releases(
                html,
                slug
            )

            catalogue[slug] = items

            print(
                f"{slug} - "
                f"{len(items)} titles"
            )

            for item in items:
                print(
                    f"{item['title']} | "
                    f"{item['type']} | "
                    f"{item['release_date']}"
                )

        except Exception as error:

            print(
                f"ERROR - {language_name}: {error}"
            )

            catalogue[slug] = []

    with open(
        "catalogue-test.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            catalogue,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 50)
    print("Saved catalogue-test.json")
    print("=" * 50)


if __name__ == "__main__":
    main()
