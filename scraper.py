import re
import requests
from bs4 import BeautifulSoup

# ==================== CONFIGURATION ====================
BASE_URL = "https://filmyfly.church"
TOTAL_PAGES = 2  # इसे बाद में अपनी जरूरत के हिसाब से बढ़ा या घटा सकते हैं
OUTPUT_PLAYLIST = "playlist.m3u"
# =======================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def scrape_movies():
    movies_data = []
    
    for page in range(1, TOTAL_PAGES + 1):
        page_url = f"{BASE_URL}/" if page == 1 else f"{BASE_URL}/?page={page}"
        print(f"Scraping page: {page_url}")
        
        soup = get_soup(page_url)
        if not soup:
            continue
            
        items = soup.find_all('div', class_='A10')
        for item in items:
            try:
                # 1. Title & Movie Link निकालना
                title_tag = item.find('div', class_='row-title')
                link_tag = item.find('a')
                if not title_tag or not link_tag:
                    continue
                
                movie_title = title_tag.get_text(strip=True)
                relative_movie_link = link_tag.get('href')
                movie_link = BASE_URL + relative_movie_link if relative_movie_link.startswith('/') else relative_movie_link
                
                # 2. Poster Image URL बदलना
                img_tag = item.find('img')
                poster_url = ""
                if img_tag:
                    raw_poster = img_tag.get('src') or img_tag.get('data-src')
                    if raw_poster:
                        poster_url = raw_poster.replace('60-65-2x', '280-380-3x')
                
                print(f"Processing movie: {movie_title}")
                
                # 3. Movie Page को बैकग्राउंड में खोलना
                movie_soup = get_soup(movie_link)
                if not movie_soup:
                    continue
                
                # 4. "Download This Movie" वाला रीडायरेक्ट लिंक ढूँढना
                dlbtn_div = movie_soup.find('div', class_='dlbtn')
                if not dlbtn_div:
                    continue
                
                redirect_a = dlbtn_div.find('a')
                if not redirect_a:
                    continue
                    
                redirect_link = redirect_a.get('href')
                
                # 5. रीडायरेक्ट लिंक को खोलकर फाइनल डाउनलोड पेज तक पहुँचना
                final_soup = get_soup(redirect_link)
                if not final_soup:
                    continue
                
                # 6. सही 1080p / HD डाउनलोड लिंक ढूँढना (फालतू/फुटर लिंक्स को छोड़कर)
                final_link = ""
                
                # पहले .dlink क्लास के अंदर वाले डाउनलोड बटन चेक करें (जो सबसे सटीक होते हैं)
                dlink_divs = final_soup.find_all('div', class_='dlink')
                if dlink_divs:
                    for dlink in reversed(dlink_divs):
                        a_tag = dlink.find('a')
                        if a_tag and a_tag.get('href'):
                            txt = a_tag.get_text().lower()
                            href = a_tag.get('href')
                            # 1080p या सबसे हाई क्वालिटी वाला बटन चुनें और contact.html से बचें
                            if ("1080" in txt or "hd" in txt or "cloud" in href) and "contact" not in href:
                                final_link = href
                                break
                
                # अगर ऊपर से न मिले, तो पेज के सभी लिंक्स में से आखिरी सही डाउनलोड लिंक ढूंढें
                if not final_link:
                    all_links = final_soup.find_all('a')
                    for a in reversed(all_links):
                        href = a.get('href')
                        txt = a.get_text().lower()
                        if href and ('1080' in txt or 'hd' in txt or 'filesdl' in href or 'drive' in href) and 'contact' not in href and 'index' not in href:
                            final_link = href
                            break
                
                if final_link:
                    movies_data.append({
                        'title': movie_title,
                        'poster': poster_url,
                        'download_link': final_link
                    })
                    print(f"Added best HD link for: {movie_title}")
                    
            except Exception as e:
                print(f"Error parsing item: {e}")
                continue
                
    return movies_data

def update_playlist(movies):
    with open(OUTPUT_PLAYLIST, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for m in movies:
            f.write(f'#EXTINF:-1 tvg-logo="{m["poster"]}" ,{m["title"]}\n')
            f.write(f'{m["download_link"]}\n')
    print(f"Playlist updated successfully with {len(movies)} items!")

if __name__ == "__main__":
    movies = scrape_movies()
    if movies:
        update_playlist(movies)
    else:
        print("No movies found.")
