
import os
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# === DOMAIN CONFIGURATION ===
BASE_URL = "https://filmyfly.family"
PLAYLIST_FILE = "playlist.m3u"
MAX_PAGES = 70

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

session = requests.Session()
session.headers.update(HEADERS)


def get_soup(url):
    """Fetch a webpage and return BeautifulSoup."""
    for attempt in range(3):
        try:
            response = session.get(url, timeout=25)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")

        except requests.RequestException as error:
            print(
                f"Fetch failed ({attempt + 1}/3): "
                f"{url} | {error}",
                flush=True
            )
            time.sleep(2)

    return None


def find_movie_blocks(soup):
    return soup.find_all("div", class_="A10")


def scrape_movies():
    m3u_entries = []
    seen_urls = set()

    for page in range(1, MAX_PAGES + 1):
        target_url = (
            BASE_URL if page == 1
            else f"{BASE_URL}/?page={page}"
        )

        print(f"\nScraping page {page}: {target_url}", flush=True)

        soup = get_soup(target_url)

        if soup is None:
            print(f"Page {page} failed; skipping.", flush=True)
            continue

        movie_blocks = find_movie_blocks(soup)

        print(
            f"Found {len(movie_blocks)} movie blocks.",
            flush=True
        )

        if not movie_blocks:
            print(
                f"No movie blocks on page {page}.",
                flush=True
            )

        for block in movie_blocks:
            try:
                link_tag = block.find("a", href=True)

                if not link_tag:
                    continue

                movie_url = urljoin(
                    BASE_URL + "/",
                    link_tag["href"]
                )

                img_tag = block.find("img")

                img_url = ""
                title = "Unknown Movie"

                if img_tag:
                    img_url = urljoin(
                        BASE_URL + "/",
                        img_tag.get("src", "")
                    )
                    title = (
                        img_tag.get("alt")
                        or img_tag.get("title")
                        or title
                    )

                title = title.strip()

                # Step 1: Movie detail page
                detail_soup = get_soup(movie_url)

                if detail_soup is None:
                    continue

                possible_dl_url = None

                for a_tag in detail_soup.find_all(
                    "a", href=True
                ):
                    href = a_tag["href"]
                    text = a_tag.get_text(" ", strip=True)
                    classes = a_tag.get("class", [])

                    if (
                        "download" in text.lower()
                        or "bg2" in classes
                        or "movie/" in href
                        or "cloud/" in href
                    ):
                        possible_dl_url = urljoin(
                            movie_url, href
                        )
                        break

                if not possible_dl_url:
                    first_a = detail_soup.find(
                        "a", href=True
                    )

                    if not first_a:
                        continue

                    possible_dl_url = urljoin(
                        movie_url, first_a["href"]
                    )

                # Step 2: Resolution / intermediate page
                res_soup = get_soup(possible_dl_url)
                target_url = None

                if res_soup:
                    candidate_links = []

                    for a_tag in res_soup.find_all(
                        "a", href=True
                    ):
                        href = urljoin(
                            possible_dl_url,
                            a_tag["href"]
                        )
                        text = a_tag.get_text(
                            " ", strip=True
                        ).lower()

                        if "1080p" in text:
                            candidate_links.append(href)

                    if candidate_links:
                        target_url = candidate_links[-1]
                    else:
                        for a_tag in res_soup.find_all(
                            "a", href=True
                        ):
                            href = urljoin(
                                possible_dl_url,
                                a_tag["href"]
                            )

                            if any(
                                host in href.lower()
                                for host in (
                                    "filesdl.in",
                                    "cloud/",
                                    "drive/",
                                )
                            ):
                                target_url = href
                                break

                if not target_url:
                    target_url = possible_dl_url

                # Step 3: Final page
                final_soup = get_soup(target_url)
                best_stream_url = None

                if final_soup:
                    for a_tag in final_soup.find_all(
                        "a", href=True
                    ):
                        href = urljoin(
                            target_url,
                            a_tag["href"]
                        )
                        lower_href = href.lower()

                        if any(
                            host in lower_href
                            for host in (
                                "pub-",
                                "r2.dev",
                                "pixeldrain.dev",
                                "fast",
                            )
                        ):
                            best_stream_url = href
                            break

                    if not best_stream_url:
                        for a_tag in final_soup.find_all(
                            "a", href=True
                        ):
                            href = urljoin(
                                target_url,
                                a_tag["href"]
                            )

                            if any(
                                path in href.lower()
                                for path in (
                                    "cloud/",
                                    "file/",
                                    "drive/",
                                )
                            ):
                                best_stream_url = href
                                break

                if not best_stream_url:
                    best_stream_url = target_url

                # Keep the existing Pixeldrain conversion.
                if "pixeldrain.dev/u/" in best_stream_url:
                    best_stream_url = best_stream_url.replace(
                        "/u/", "/api/file/"
                    )

                if best_stream_url in seen_urls:
                    continue

                seen_urls.add(best_stream_url)

                # Prevent quotation marks breaking M3U metadata.
                safe_title = (
                    title.replace('"', "'")
                    .replace("\r", " ")
                    .replace("\n", " ")
                )
                safe_logo = (
                    img_url.replace('"', "%22")
                    .replace("\r", "")
                    .replace("\n", "")
                )

                entry = (
                    f'#EXTINF:-1 tvg-logo="{safe_logo}" '
                    f'group-title="🍿4K Movies Latest",'
                    f'{safe_title}\n'
                    f'{best_stream_url}'
                )

                m3u_entries.append(entry)

                print(f"Added: {safe_title}", flush=True)

                # Avoid hammering the website.
                time.sleep(0.3)

            except Exception as error:
                print(
                    f"Movie processing error: {error}",
                    flush=True
                )
                continue

    return m3u_entries


def update_playlist_file(entries):
    if not entries:
        raise RuntimeError(
            "No movies were scraped. "
            "Existing playlist will not be overwritten."
        )

    content = "#EXTM3U\n" + "\n".join(entries) + "\n"

    temp_file = PLAYLIST_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        file.write(content)

    os.replace(temp_file, PLAYLIST_FILE)

    print(
        f"\nPlaylist updated: {len(entries)} entries.",
        flush=True
    )


if __name__ == "__main__":
    print("Starting movie playlist scraper...", flush=True)

    movies = scrape_movies()
    update_playlist_file(movies)

    print("Scraper completed successfully.", flush=True)
