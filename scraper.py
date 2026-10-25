import os
import re
from bs4ational import BeautifulSoup
from bs4 import BeautifulSoup
import requests

# === DOMAIN CONFIGURATION ===
# Agar kabhi domain badle, toh bas yahan naya URL daal dena (Sab jagah apne aap apply ho jayega)
BASE_URL = "https://filmyfly.family"
PLAYLIST_FILE = "playlist.m3u"
MAX_PAGES = 40  # Page 1 se 40 tak crawl karega

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
    m3u_entries = []
    
    # Page 1 se lekar 40 tak loop chalana
    for page in range(1, MAX_PAGES + 1):
        if page == 1:
            target_url = BASE_URL
        else:
            target_url = f"{BASE_URL}/?page={page}"
            
        print(f"Scraping Page {page}: {target_url}")
        soup = get_soup(target_url)
        if not soup:
            print(f"Failed to fetch page {page}, skipping...")
            continue

        movie_blocks = soup.find_all('div', class_='A10')
        print(f"Found {len(movie_blocks)} movie blocks on page {page}.")

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

                # Step 1: Movie detail page par jana
                detail_soup = get_soup(movie_href)
                if not detail_soup:
                    continue

                possible_dl_href = None
                for a_tag in detail_soup.find_all('a', href=True):
                    href = a_tag['href']
                    text = a_tag.get_text()
                    if 'Download' in text or 'bg2' in a_tag.get('class', []) or 'movie/' in href or 'cloud/' in href:
                        possible_dl_href = href
                        break

                if not possible_dl_href:
                    first_a = detail_soup.find('a', href=True)
                    if first_a:
                        possible_dl_href = first_a['href']
                    else:
                        continue

                if not possible_dl_href.startswith('http'):
                    possible_dl_href = BASE_URL + possible_dl_href

                # Step 2: Resolution / Intermediate page
                res_soup = get_soup(possible_dl_href)
                
                target_href = None
                if res_soup:
                    candidate_links = []
                    for a_tag in res_soup.find_all('a', href=True):
                        text = a_tag.get_text()
                        href = a_tag['href']
                        if '1080p' in text:
                            candidate_links.append(href)
                    
                    if candidate_links:
                        target_href = candidate_links[-1]
                    else:
                        for a_tag in res_soup.find_all('a', href=True):
                            href = a_tag['href']
                            if 'filesdl.in' in href or 'cloud/' in href or 'drive/' in href:
                                target_href = href
                                break
                
                if not target_href:
                    target_href = possible_dl_href

                if not target_href.startswith('http'):
                    target_href = BASE_URL + target_href

                # Step 3: Final Download Page
                final_soup = get_soup(target_href)
                best_stream_url = None

                if final_soup:
                    for a_tag in final_soup.find_all('a', href=True):
                        href = a_tag['href']
                        if 'pub-' in href or 'r2.dev' in href or 'pixeldrain.dev' in href or 'fast' in href:
                            best_stream_url = href
                            break
                    
                    if not best_stream_url:
                        for a_tag in final_soup.find_all('a', href=True):
                            href = a_tag['href']
                            if 'cloud/' in href or 'file/' in href or 'drive/' in href:
                                best_stream_url = BASE_URL + href if not href.startswith('http') else href
                                break
                
                if not best_stream_url:
                    best_stream_url = target_href

                if 'pixeldrain.dev/u/' in best_stream_url:
                    best_stream_url = best_stream_url.replace('/u/', '/api/file/')

                tvg_logo = img_url if img_url else ''
                m3u_entry = f'#EXTINF:-1 tvg-logo="{tvg_logo}" group-title="🍿4K Movies Latest",{title}\n{best_stream_url}\n'
                
                # Duplicate entries se bachne ke liye check karna
                if m3u_entry not in m3u_entries:
                    m3u_entries.append(m3u_entry)
                    print(f"Added: {title}")

            except Exception as e:
                continue

    return m3u_entries

def update_playlist_file(entries):
    header = "#EXTM3U\n"
    content = header + "\n".join(entries) if entries else header + "# No movies found currently\n"

    with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Playlist updated successfully with {len(entries)} items!")

if __name__ == "__main__":
    movie_entries = scrape_movies()
    update_playlist_file(movie_entries)
