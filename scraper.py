import os
import re
from bs4 import BeautifulSoup
import requests

BASE_URL = "https://filmyfly.family"
PLAYLIST_FILE = "playlist.m3u"

def get_soup(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def scrape_movies():
    print("Fetching main page...")
    soup = get_soup(BASE_URL)
    if not soup:
        return []

    m3u_entries = []
    movie_blocks = soup.find_all('div', class_='A10')
    print(f"Found {len(movie_blocks)} movie blocks.")

    for block in movie_blocks:
        try:
            link_tag = block.find('a', href=True)
            if not link_tag:
                continue
            
            movie_href = link_tag['href']
            if not movie_href.startswith('http'):
                movie_href = BASE_URL + movie_href

            img_tag = block.find('img')
            img_url = img_tag['src'] if img_tag else ''
            title = img_tag['alt'] if img_tag and 'alt' in img_tag.attrs else 'Unknown Movie'

            print(f"Processing movie: {title}")

            # Step 1: Movie detail page par jana
            detail_soup = get_soup(movie_href)
            if not detail_soup:
                continue

            # Us page par jitne bhi links hain, unme se filesdl ya cloud links dhoondna
            target_href = None
            for a_tag in detail_soup.find_all('a', href=True):
                href = a_tag['href']
                text = a_tag.get_text()
                # 1080p ya download links ko target karna
                if '1080p' in text or 'Download' in text or 'filesdl' in href or 'cloud' in href:
                    if not href.startswith('http'):
                        target_href = BASE_URL + href
                    else:
                        target_href = href
                    break

            if not target_href:
                continue

            # Step 2: Us link ko background me open karna
            final_soup = get_soup(target_href)
            if not final_soup:
                # Agar seedha direct link hi mil gaya ho toh wahi use kar lo
                if 'pub-' in target_href or 'r2.dev' in target_href or 'pixeldrain.dev' in target_href:
                    best_stream_url = target_href
                else:
                    continue
            else:
                best_stream_url = None
                # Final page se r2 ya stream link nikalna
                for a_tag in final_soup.find_all('a', href=True):
                    href = a_tag['href']
                    if 'pub-' in href or 'r2.dev' in href or 'pixeldrain.dev' in href or 'fast' in href:
                        best_stream_url = href
                        break
                
                # Agar upar wala na mile toh koi bhi valid download link utha lo
                if not best_stream_url:
                    for a_tag in final_soup.find_all('a', href=True):
                        href = a_tag['href']
                        if 'cloud/' in href or 'file/' in href:
                            best_stream_url = BASE_URL + href if not href.startswith('http') else href
                            break

            if not best_stream_url:
                continue

            # Pixeldrain URL fix
            if 'pixeldrain.dev/u/' in best_stream_url:
                best_stream_url = best_stream_url.replace('/u/', '/api/file/')

            tvg_logo = img_url if img_url else ''
            m3u_entry = f'#EXTINF:-1 tvg-logo="{tvg_logo}" group-title="🍿4K Movies Latest",{title}\n{best_stream_url}\n'
            m3u_entries.append(m3u_entry)
            print(f"Added successfully: {title}")

        except Exception as e:
            print(f"Error processing {title}: {e}")
            continue

    return m3u_entries

def update_playlist_file(entries):
    header = "#EXTM3U\n"
    content = header + "\n".join(entries) if entries else header + "# No movies found currently\n"

    with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Playlist updated with {len(entries)} items!")

if __name__ == "__main__":
    movie_entries = scrape_movies()
    update_playlist_file(movie_entries)
