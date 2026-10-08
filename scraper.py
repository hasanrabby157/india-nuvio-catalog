import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode

BASE_URL = "https://ottweek.com/"

LANGUAGES = {
    "hindi": "Hindi",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "malayalam": "Malayalam",
    "bengali": "Bengali",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 12) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
    )
}


def clean_text(text):
    if not text:
        return None

    text = re.sub(r"\s+", " ", text).strip()

    # Remove the unwanted Trending labels if they ever appear
    text = re.sub(r"^All week\s+", "", text, flags=re.I)
    text = re.sub(r"\s+Day\s+\d+$", "", text, flags=re.I)

    return text.strip()


def get_page(language):
    params = {
        "language": language
    }

    response = requests.get(
        BASE_URL,
        params=params,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.text


def parse_language_page(html, language):
    soup = BeautifulSoup(html, "html.parser")

    items = []

    # Find the main release heading
    release_heading = None

    for heading in soup.find_all(["h1", "h2", "h3"]):
        text = clean_text(heading.get_text(" ", strip=True))

        if text and "new release" in text.lower():
            release_heading = heading
            break

    # Main content area
    main = soup.find("main")

    if not main:
        main = soup

    # Look for links/cards that belong to actual OTT titles.
    # Avoid the "Trending now" section.
    seen = set()

    for link in main.find_all("a", href=True):

        title = clean_text(link.get_text(" ", strip=True))

        if not title:
            continue

        href = link.get("href", "")

        # Skip navigation/filter links
        if (
            href.startswith("#")
            or "language=" in href
            or "platform=" in href
            or "genre=" in href
            or "type=" in href
        ):
            continue

        # Skip obvious navigation text
        lower_title = title.lower()

        if lower_title in {
            "view trailer",
            "show more",
            "clear all",
            "movies",
            "web series",
            "new releases",
            "trending now",
        }:
            continue

        # Skip the fake/trending entries
        if lower_title.startswith("all week"):
            continue

        if "day " in lower_title and "week" in lower_title:
            continue

        # Need a reasonably title-like link
        if len(title) < 2:
            continue

        # Don't duplicate
        key = (title.lower(), href)

        if key in seen:
            continue

        seen.add(key)

        # Find surrounding card/container
        card = link

        for _ in range(5):
            if card.parent:
                card = card.parent

                card_text = card.get_text(" ", strip=True)

                # Stop if this looks like an actual release card
                if (
                    "Movie" in card_text
                    or "Series" in card_text
                    or "In " + LANGUAGES[language] in card_text
                ):
                    break

        card_text = card.get_text(" ", strip=True)

        # Make sure this actually belongs to the requested language
        if f"In {LANGUAGES[language]}" not in card_text:
            continue

        # Determine type
        item_type = None

        if re.search(r"\bMovie\b", card_text):
            item_type = "movie"

        elif re.search(r"\bSeries\b", card_text):
            item_type = "series"

        if not item_type:
            continue

        # Find date
        date_match = re.search(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"\s+\d{1,2},\s+\d{4}",
            card_text
        )

        release_date = date_match.group(0) if date_match else None

        items.append({
            "title": title,
            "type": item_type,
            "language": LANGUAGES[language],
            "release_date": release_date,
            "url": href
        })

    # Remove duplicates by title/type
    unique = []
    seen_titles = set()

    for item in items:
        key = (
            item["title"].lower(),
            item["type"],
            item["language"]
        )

        if key in seen_titles:
            continue

        seen_titles.add(key)
        unique.append(item)

    return unique


def main():
    catalogue = {}

    for slug, language_name in LANGUAGES.items():

        print(f"\n========== {language_name} ==========")

        try:
            html = get_page(slug)

            items = parse_language_page(html, slug)

            catalogue[slug] = items

            print(f"Found {len(items)} items")

            for item in items[:10]:
                print(
                    f"{item['title']} | "
                    f"{item['type']} | "
                    f"{item['release_date']}"
                )

        except Exception as e:
            print(f"ERROR for {language_name}: {e}")
            catalogue[slug] = []

    with open(
        "catalogue-test.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            catalogue,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("\n================================")
    print("Saved catalogue-test.json")
    print("================================")


if __name__ == "__main__":
    main()v
