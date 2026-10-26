import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

=== DOMAIN CONFIGURATION ===

BASE_URL = "https://filmyfly.family"
PLAYLIST_FILE = "playlist.m3u"
MAX_PAGES = 70

def get_soup(url):
try:
headers = {
"User-Agent": (
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
"AppleWebKit/537.36 (KHTML, like Gecko) "
"Chrome/120.0.0.0 Safari/537.36"
)
}

    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    if response.status_code == 200:
        return BeautifulSoup(response.text, "html.parser")

    print(f"HTTP {response.status_code}: {url}")

except requests.RequestException as e:
    print(f"Error fetching {url}: {e}")

return None

def scrape_movies():
m3u_entries = []
seen_urls = set()

for page in range(1, MAX_PAGES + 1):

    if page == 1:
        target_url = BASE_URL
    else:
        target_url = f"{BASE_URL}/?page={page}"

    print(f"\nScraping Page {page}: {target_url}")

    soup = get_soup(target_url)

    if soup is None:
        print(f"Failed to fetch page {page}, skipping...")
        continue

    movie_blocks = soup.find_all("div", class_="A10")

    print(f"Found {len(movie_blocks)} movie blocks.")

    for block in movie_blocks:
        try:
            link_tag = block.find("a", href=True)

            if not link_tag:
                continue

            movie_href = urljoin(
                target_url,
                link_tag["href"]
            )

            img_tag = block.find("img")

            if img_tag:
                img_url = urljoin(
                    target_url,
                    img_tag.get("src", "")
                )
                title = img_tag.get(
                    "alt",
                    "Unknown Movie"
                )
            else:
                img_url = ""
                title = link_tag.get_text(
                    " ",
                    strip=True
                ) or "Unknown Movie"

            print(f"Checking movie: {title}")

            # Step 1: Movie detail page
            detail_soup = get_soup(movie_href)

            if detail_soup is None:
                continue

            possible_dl_href = None

            for a_tag in detail_soup.find_all(
                "a",
                href=True
            ):
                href = a_tag["href"]
                text = a_tag.get_text(
                    " ",
                    strip=True
                ).lower()

                classes = a_tag.get("class", [])

                if (
                    "download" in text
                    or "bg2" in classes
                    or "movie/" in href
                    or "cloud/" in href
                ):
                    possible_dl_href = urljoin(
                        movie_href,
                        href
                    )
                    break

            if not possible_dl_href:
                print("Download page link not found.")
                continue

            # Step 2: Resolution/intermediate page
            res_soup = get_soup(possible_dl_href)
            target_href = None

            if res_soup:
                candidate_links = []

                for a_tag in res_soup.find_all(
                    "a",
                    href=True
                ):
                    text = a_tag.get_text(
                        " ",
                        strip=True
                    ).lower()

                    href = urljoin(
                        possible_dl_href,
                        a_tag["href"]
                    )

                    if "1080p" in text:
                        candidate_links.append(href)

                if candidate_links:
                    target_href = candidate_links[-1]

                else:
                    for a_tag in res_soup.find_all(
                        "a",
                        href=True
                    ):
                        href = urljoin(
                            possible_dl_href,
                            a_tag["href"]
                        )

                        if (
                            "filesdl.in" in href
                            or "cloud/" in href
                            or "drive/" in href
                        ):
                            target_href = href
                            break

            if not target_href:
                target_href = possible_dl_href

            # Step 3: Final page
            final_soup = get_soup(target_href)
            best_stream_url = None

            if final_soup:
                for a_tag in final_soup.find_all(
                    "a",
                    href=True
                ):
                    href = urljoin(
                        target_href,
                        a_tag["href"]
                    )

                    if (
                        "pub-" in href
                        or "r2.dev" in href
                        or "pixeldrain.dev" in href
                        or "filesdl.in" in href
                    ):
                        best_stream_url = href
                        break

                if not best_stream_url:
                    for a_tag in final_soup.find_all(
                        "a",
                        href=True
                    ):
                        href = urljoin(
                            target_href,
                            a_tag["href"]
                        )

                        if (
                            "cloud/" in href
                            or "file/" in href
                            or "drive/" in href
                        ):
                            best_stream_url = href
                            break

            if not best_stream_url:
                best_stream_url = target_href

            # Avoid duplicate URLs
            if best_stream_url in seen_urls:
                continue

            seen_urls.add(best_stream_url)

            # Create M3U entry
            safe_title = (
                title.replace("\n", " ")
                .replace("\r", " ")
                .replace('"', "'")
                .strip()
            )

            m3u_entry = (
                f'#EXTINF:-1 tvg-logo="{img_url}" '
                f'group-title="🍿4K Movies Latest",'
                f'{safe_title}\n'
                f'{best_stream_url}'
            )

            m3u_entries.append(m3u_entry)

            print(f"Added: {safe_title}")
            print(f"Link: {best_stream_url}")

        except Exception as e:
            print(f"Error processing movie: {e}")
            continue

return m3u_entries

def update_playlist_file(entries):
content = "#EXTM3U\n"

if entries:
    content += "\n".join(entries) + "\n"
else:
    content += "# No movies found currently\n"

with open(
    PLAYLIST_FILE,
    "w",
    encoding="utf-8"
) as f:
    f.write(content)

print(
    f"\nPlaylist updated successfully "
    f"with {len(entries)} items!"
)

if name == "main":
movie_entries = scrape_movies()
update_playlist_file(movie_entries)
