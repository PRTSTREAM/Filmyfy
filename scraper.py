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

            dl_link_tag = detail_soup.find('a', class_='bg2')
            if not dl_link_tag or 'href' not in dl_link_tag.attrs:
                continue

            inner_dl_href = dl_link_tag['href']
            if not inner_dl_href.startswith('http'):
                inner_dl_href = BASE_URL + inner_dl_href

            # Step 2: Resolution selection page par jana
            res_soup = get_soup(inner_dl_href)
            if not res_soup:
                continue

            # Strict 1080p target filter (Chahe WEB-DL ho, HD ho ya 10bit ho)
            target_href = None
            candidate_links = []
            for a_tag in res_soup.find_all('a', href=True):
                text = a_tag.get_text()
                if '1080p' in text:
                    candidate_links.append(a_tag['href'])
            
            # Agar 1080p links milte hain toh sabse behtareen/aakhri wala uthao
            if candidate_links:
                target_href = candidate_links[-1]
            
            # Agar 1080p explicit na mile toh koi bhi available filesdl/drive link utha lo taaki playlist khali na rahe
            if not target_href:
                all_links = [a['href'] for a in res_soup.find_all('a', href=True) if 'filesdl.in' in a['href'] or 'cloud' in a['href'] or 'drive' in a['href']]
                if all_links:
                    target_href = all_links[-1]

            if not target_href:
                print(f"Skipping {title}: No valid link found.")
                continue

            if not target_href.startswith('http'):
                target_href = BASE_URL + target_href

            # Step 3: Final download page par jana
            final_soup = get_soup(target_href)
            if not final_soup:
                if 'pub-' in target_href or 'r2.dev' in target_href or 'pixeldrain.dev' in target_href:
                    best_stream_url = target_href
                else:
                    continue
            else:
                best_stream_url = None
                for a_tag in final_soup.find_all('a', href=True):
                    href = a_tag['href']
                    if 'pub-' in href or 'r2.dev' in href or 'pixeldrain.dev' in href or 'fast' in href:
                        best_stream_url = href
                        break
                
                # Agar direct r2 link na mile toh page par jo bhi pehla cloud/drive link mile use utha lo
                if not best_stream_url:
                    for a_tag in final_soup.find_all('a', href=True):
                        href = a_tag['href']
                        if 'cloud/' in href or 'file/' in href or 'drive/' in href:
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
            print(f"Added: {title}")

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
