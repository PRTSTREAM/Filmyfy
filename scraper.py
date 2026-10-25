import os
import re
from bs4 import BeautifulSoup
import requests

BASE_URL = "https://filmyfly.family"
PLAYLIST_FILE = "playlist.m3u"


def get_soup(url):
  try:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code == 200:
      return BeautifulSoup(response.text, "html.parser")
  except Exception as e:
    print(f"Error fetching {url}: {e}")
  return None


def scrape_movies():
  print("Fetching main page...")
  soup = get_soup(BASE_URL)
  if not soup:
    return []

  m3u_entries = []

  # Latest movies blocks find karna
  movie_blocks = soup.find_all("div", class_="A10")
  print(f"Found {len(movie_blocks)} movie blocks.")

  for block in movie_blocks:
    try:
      # Title, Image, aur Movie Link nikalna
      link_tag = block.find("a", href=True)
      if not link_tag:
        continue

      movie_href = link_tag["href"]
      if not movie_href.startswith("http"):
        movie_href = BASE_URL + movie_href

      img_tag = block.find("img")
      img_url = img_tag["src"] if img_tag else ""
      title = (
          img_tag["alt"]
          if img_tag and "alt" in img_tag.attrs
          else "Unknown Movie"
      )

      print(f"Processing movie: {title}")

      # Step 1: Movie ke detail page par jana
      detail_soup = get_soup(movie_href)
      if not detail_soup:
        continue

      # Step 2: Download buttons wale page/section ko find karna
      # Example: <a class="bg2" href="...">Download 480p 720p 1080p [HEVC]</a>
      dl_link_tag = detail_soup.find("a", class_="bg2")
      if not dl_link_tag or "href" not in dl_link_tag.attrs:
        continue

      inner_dl_href = dl_link_tag["href"]
      if not inner_dl_href.startswith("http"):
        inner_dl_href = BASE_URL + inner_dl_href

      # Step 3: Final download links wale page par jana
      final_soup = get_soup(inner_dl_href)
      if not final_soup:
        continue

      # High quality link dhundna (Preference: Cloud Direct / R2 / Pixeldrain / 1080p)
      best_stream_url = None

      # 1. Check for Cloud Direct (.r2.dev link)
      r2_link = final_soup.find(
          "a", class_=lambda x: x and "download-link" in x
      )
      if r2_link and "href" in r2_link.attrs:
        best_stream_url = r2_link["href"]

      # 2. Agar R2 nahi mila, toh Pixeldrain ya doosra dekho
      if not best_stream_url:
        for a_tag in final_soup.find_all("a", href=True):
          href = a_tag["href"]
          if "pixeldrain.dev" in href or "filesdl.in" in href or "r2.dev" in href:
            best_stream_url = href
            break

      if not best_stream_url:
        print(f"Skipping {title}: No valid high quality stream link found.")
        continue

      # Pixeldrain URL fix: pixeldrain.dev/u/ID?download -> pixeldrain.dev/api/file/ID?download
      if "pixeldrain.dev/u/" in best_stream_url:
        best_stream_url = best_stream_url.replace(
            "/u/", "/api/file/"
        )

      # M3U Format entry banana under group "🍿4K Movies Latest"
      tvg_logo = img_url if img_url else ""
      m3u_entry = (
          f'#EXTINF:-1 tvg-logo="{tvg_logo}"'
          f' group-title="🍿4K Movies Latest",{title}\n{best_stream_url}\n'
      )
      m3u_entries.append(m3u_entry)

    except Exception as e:
      print(f"Error processing a block: {e}")
      continue

  return m3u_entries


def update_playlist_file(entries):
  if not entries:
    print("No entries found to update.")
    return

  header = "#EXTM3U\n"
  content = header + "\n".join(entries)

  with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
    f.write(content)
  print(f"Playlist updated successfully with {len(entries)} items!")


if __name__ == "__main__":
  movie_entries = scrape_movies()
  update_playlist_file(movie_entries)
