import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://ottweek.com/"

LANGUAGES = {
    "hindi": "Hindi",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "malayalam": "Malayalam",
    "bengali": "Bengali",
}


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def get_page(language):
    url = f"{BASE_URL}?kind=all&language={language}"
    
    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; IndiaNuvioCatalog/1.0)"
        },
        timeout=30,
    )
    
    response.raise_for_status()
    return response.text


def scrape_language(language):
    html = get_page(language)
    soup = BeautifulSoup(html, "html.parser")

    results = []

    # Find title links pointing to OTTweek movie/tv pages
    links = soup.select('a[href*="/title/"]')

    seen = set()

    for link in links:
        href = link.get("href", "")
        title = clean(link.get_text(" ", strip=True))

        if not href or not title:
            continue

        if href in seen:
            continue

        seen.add(href)

        full_url = urljoin(BASE_URL, href)

        # Determine whether it is a movie or series from URL
        if "/title/movie/" in href:
            content_type = "movie"
        elif "/title/tv/" in href:
            content_type = "series"
        else:
            continue

        # Look around the title for metadata
        parent = link.parent
        block_text = clean(parent.get_text(" ", strip=True))

        # Try to find IMDb rating
        rating_match = re.search(r"(\d+(?:\.\d+)?)\s*IMDb", block_text)
        rating = rating_match.group(1) if rating_match else None

        # Try to find release date
        date_match = re.search(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"\s+\d{1,2},\s+\d{4}",
            block_text,
        )
        release_date = date_match.group(0) if date_match else None

        # Try to find poster
        image = None
        img = parent.find("img")

        if img:
            image = img.get("src") or img.get("data-src")

        results.append({
            "title": title,
            "type": content_type,
            "language": LANGUAGES[language],
            "release_date": release_date,
            "rating": rating,
            "poster": image,
            "ottweek_url": full_url,
        })

    return results


def main():
    catalogue = {}

    for code, language_name in LANGUAGES.items():
        print(f"Scraping {language_name}...")

        try:
            items = scrape_language(code)

            catalogue[language_name] = items

            print(
                f"{language_name}: {len(items)} titles found"
            )

        except Exception as e:
            print(
                f"ERROR - {language_name}: {e}"
            )
            catalogue[language_name] = []

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

    total = sum(
        len(items)
        for items in catalogue.values()
    )

    print()
    print(f"TOTAL TITLES: {total}")
    print("Saved: catalogue-test.json")


if __name__ == "__main__":
    main()
