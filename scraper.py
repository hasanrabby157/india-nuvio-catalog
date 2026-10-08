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

    return response.text, response.url


def find_release_section(soup):
    """
    Find the heading:
    'X new <language> releases on OTT this week'

    Everything before the Trending section belongs to
    the actual release grid.
    """

    heading = None

    for h2 in soup.find_all("h2"):
        text = clean(h2.get_text(" ", strip=True)).lower()

        if "new" in text and "releases on ott" in text:
            heading = h2
            break

    if not heading:
        return None

    return heading


def parse_releases(html, language):
    soup = BeautifulSoup(html, "html.parser")

    release_heading = find_release_section(soup)

    if not release_heading:
        print("Could not find release section")
        return []

    items = []

    # Everything after the release heading is examined,
    # but we STOP at "Trending now".
    current = release_heading.find_next()

    while current:

        # Stop before Trending now
        if current.name in ["h2", "h3"]:
            text = clean(current.get_text(" ", strip=True)).lower()

            if "trending now" in text:
                break

        current = current.find_next()

    # Easier and more reliable:
    # use all headings (h3) between release heading and Trending.
    in_release_section = False

    for element in soup.find_all(["h2", "h3"]):

        text = clean(element.get_text(" ", strip=True))

        lower = text.lower()

        if element == release_heading:
            in_release_section = True
            continue

        if in_release_section and "trending now" in lower:
            break

        if not in_release_section:
            continue

        # h3 titles are actual release titles
        if element.name != "h3":
            continue

        title = text

        if not title:
            continue

        # Ignore navigation/metadata
        ignored = {
            "new ott releases by language",
            "guides & original writing",
        }

        if lower in ignored:
            continue

        # Find the nearest parent/card
        card = element

        for _ in range(6):
            if card.parent:
                card = card.parent

            card_text = clean(
                card.get_text(" ", strip=True)
            )

            # Actual cards normally contain Movie or Series
            if re.search(
                r"\b(Movie|Series)\b",
                card_text,
                re.IGNORECASE
            ):
                break

        card_text = clean(
            card.get_text(" ", strip=True)
        )

        # Determine movie / series
        item_type = None

        # Search the text immediately around the card
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

        # Find title link
        link = None

        # Usually the title/card contains a link
        for a in card.find_all("a", href=True):

            href = a.get("href", "")

            if href.startswith("/"):
                full_url = urljoin(BASE_URL, href)

                # Avoid filter/navigation links
                if (
                    "/language/" not in href
                    and "platform" not in href
                    and "genre" not in href
                ):
                    link = full_url
                    break

        item = {
            "title": title,
            "type": item_type,
            "language": LANGUAGES[language],
            "release_date": release_date,
            "url": link,
        }

        # Prevent duplicates
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


def main():

    catalogue = {}

    for slug, language_name in LANGUAGES.items():

        print()
        print("=" * 50)
        print(language_name)
        print("=" * 50)

        try:

            html, final_url = get_page(slug)

            items = parse_releases(
                html,
                slug
            )

            catalogue[slug] = items

            print(
                f"{language_name}: "
                f"{len(items)} titles"
            )

            for item in items[:10]:

                print(
                    f"{item['title']} | "
                    f"{item['type']} | "
                    f"{item['release_date']}"
                )

        except Exception as error:

            print(
                f"ERROR - {language_name}: "
                f"{error}"
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
