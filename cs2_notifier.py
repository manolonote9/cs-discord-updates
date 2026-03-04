import feedparser
import requests
import os
import re
import json
from datetime import datetime

# ==============================
# CONFIG
# ==============================
RSS_SOURCES = [
    "https://store.steampowered.com/feeds/news/app/730/",
    "https://blog.counter-strike.net/index.php/category/updates/feed/",
    "https://steamcommunity.com/games/730/rss/"
]

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
LAST_UPDATE_FILE = "last_update.txt"

# ==============================
# HTML CLEANER (nested lists)
# ==============================
def clean_html(raw_html):
    """
    Cleans HTML from the Steam feed and correctly formats nested lists for Discord.
    """

    # --- Recursive function for <ul>/<li> lists ---
    def parse_list(html):
        # Replace sub-lists first
        def sub_list(match):
            sub = match.group(1)
            # Replace <li> inside the sublist (Discord applies auto-indent with -)
            sub = re.sub(r'<li>(.*?)</li>', r'  - \1', sub, flags=re.DOTALL)
            # Process any nested <ul> within
            sub = re.sub(r'<ul>(.*?)</ul>', sub_list, sub, flags=re.DOTALL)
            return sub

        html = re.sub(r'<ul>(.*?)</ul>', sub_list, html, flags=re.DOTALL)
        # Replace main <li> items
        html = re.sub(r'<li>(.*?)</li>', r'- \1', html, flags=re.DOTALL)
        return html

    cleantext = parse_list(raw_html)

    # --- Clean remaining HTML ---
    cleantext = re.sub(r'<(br|p|/li|/ul|/p)>', '\n', cleantext)
    cleantext = re.sub(r'<.*?>', '', cleantext)
    cleantext = cleantext.replace('\r\n', '\n').replace('\r', '\n')
    cleantext = cleantext.strip()

    # --- Line by line to clean spaces and breaks ---
    final_lines = []
    for line in cleantext.split('\n'):
        content = line.strip()
        if content:
            final_lines.append(content)
    
    # Add a line break between main sections
    result = '\n'.join(final_lines)
    result = re.sub(r'\n(\[.*?\]|\b[A-Z\s]{4,}\b)', r'\n\n\1', result)

    # --- Protect technical identifiers ---
    def protect_identifiers(match):
        token = match.group(0)
        if "_" in token or "." in token or (any(c.isupper() for c in token[1:]) and token[0].isupper()):
            return f"`{token}`"
        return token

    result = re.sub(r'\b[A-Za-z_][A-Za-z0-9_.]*\b', protect_identifiers, result)
    return result

# ==============================
# STORAGE
# ==============================
def get_last_saved_id():
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def save_last_id(entry_id):
    with open(LAST_UPDATE_FILE, "w", encoding="utf-8") as f:
        f.write(entry_id)

# ==============================
# DISCORD PAYLOAD
# ==============================
def build_payload(entry):
    content = ""
    if 'content' in entry:
        content = entry.content[0].value
    else:
        content = entry.get('summary', entry.get('description', ''))

    clean_content = clean_html(content)
    
    # Add visual separator only if there is content
    if clean_content:
        clean_content = clean_content + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Safe limit for embed description = 4096
    if len(clean_content) > 4000:
        clean_content = clean_content[:3990] + "..."

    image_url = "https://cdn.akamai.steamstatic.com/steam/apps/730/capsule_617x353.jpg"
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    payload = {
        "embeds": [{
            "title": f"✨ {entry.title}",
            "description": clean_content,
            "url": entry.link,
            "color": 3092790,
            "image": {
                "url": image_url
            },
            "footer": {
                "text": f"Updated: {current_date}",
            }
        }],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,  # LINK button
                        "label": "View Full Notes ↗️",
                        "url": entry.link
                    }
                ]
            }
        ]
    }

    return payload

# ==============================
# DISCORD SENDER
# ==============================
def send_to_discord(entry):
    payload = build_payload(entry)
    if not DISCORD_WEBHOOK_URL:
        # Print payload for debugging if no webhook is set
        print(json.dumps(payload, indent=4, ensure_ascii=False))
        return
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code in (200, 204):
        print("Message sent successfully.")
    else:
        print(f"Error {response.status_code}: {response.text}")

# ==============================
# MAIN
# ==============================
def main():
    feed = None
    for url in RSS_SOURCES:
        try:
            response = requests.get(
                url,
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=10
            )
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                if feed.entries:
                    break
        except Exception:
            continue

    if not feed or not feed.entries:
        return

    latest_entry = feed.entries[0]
    latest_id = getattr(latest_entry, 'id', latest_entry.link)
    last_id = get_last_saved_id()

    # Send update if ID is new or if testing without a webhook
    if latest_id != last_id or not DISCORD_WEBHOOK_URL:
        send_to_discord(latest_entry)
        if DISCORD_WEBHOOK_URL:
            save_last_id(latest_id)

if __name__ == "__main__":
    main()
