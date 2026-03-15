
import requests
import re
import pandas as pd

# Scrapes song data from the Supernatural Fandom wiki page using the MediaWiki API.
# Produces a table with: Season, Song, Artist

API_URL = "https://supernatural.fandom.com/api.php"
PAGE = "Supernatural_Music"

def fetch_wikitext():
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": PAGE
    }
    r = requests.get(API_URL, params=params)
    r.raise_for_status()
    data = r.json()
    page = next(iter(data["query"]["pages"].values()))
    return page["revisions"][0]["slots"]["main"]["*"]

def parse_songs(text):
    rows = []
    current_season = None

    season_pattern = re.compile(r"=+\s*Season\s+(\d+)\s*=+", re.IGNORECASE)
    song_pattern = re.compile(r'\*\s*"([^"]+)"\s*[–-]\s*([^\n]+)')

    for line in text.splitlines():
        s = season_pattern.search(line)
        if s:
            current_season = int(s.group(1))
            continue

        m = song_pattern.search(line)
        if m and current_season:
            song = m.group(1).strip()
            artist = m.group(2).strip()
            rows.append({
                "season": current_season,
                "song": song,
                "artist": artist
            })

    return rows

def main():
    wikitext = fetch_wikitext()
    songs = parse_songs(wikitext)
    df = pd.DataFrame(songs)
    df.to_csv("supernatural_soundtrack.csv", index=False)
    df.to_excel("supernatural_soundtrack.xlsx", index=False)
    print("Exported soundtrack dataset.")

if __name__ == "__main__":
    main()
