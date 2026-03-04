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
# HTML CLEANER (listas anidadas)
# ==============================
def clean_html(raw_html):
    """
    Limpia HTML del feed de Steam y formatea correctamente listas anidadas para Discord.
    """

    # --- Función recursiva para listas <ul>/<li> ---
    def parse_list(html):
        # Reemplaza sub-listas primero
        def sub_list(match):
            sub = match.group(1)
            # Reemplaza <li> dentro de la sublista (Discord aplica sangría automática con -)
            sub = re.sub(r'<li>(.*?)</li>', r'  - \1', sub, flags=re.DOTALL)
            # Procesa cualquier <ul> anidado dentro
            sub = re.sub(r'<ul>(.*?)</ul>', sub_list, sub, flags=re.DOTALL)
            return sub

        html = re.sub(r'<ul>(.*?)</ul>', sub_list, html, flags=re.DOTALL)
        # Reemplaza los <li> principales
        html = re.sub(r'<li>(.*?)</li>', r'- \1', html, flags=re.DOTALL)
        return html

    cleantext = parse_list(raw_html)

    # --- Limpiar HTML restante ---
    cleantext = re.sub(r'<(br|p|/li|/ul|/p)>', '\n', cleantext)
    cleantext = re.sub(r'<.*?>', '', cleantext)
    cleantext = cleantext.replace('\r\n', '\n').replace('\r', '\n')
    cleantext = cleantext.strip()

    # --- Línea por línea para limpiar espacios y saltos ---
    final_lines = []
    for line in cleantext.split('\n'):
        content = line.strip()
        if content:
            final_lines.append(content)
    
    # Añadir un salto de línea entre secciones principales
    result = '\n'.join(final_lines)
    result = re.sub(r'\n(\[.*?\]|\b[A-Z\s]{4,}\b)', r'\n\n\1', result)

    # --- Proteger identificadores técnicos ---
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
    
    # Añadir separador visual solo si hay contenido
    if clean_content:
        clean_content = clean_content + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Límite seguro embed description = 4096
    if len(clean_content) > 4000:
        clean_content = clean_content[:3990] + "..."

    image_url = "https://cdn.akamai.steamstatic.com/steam/apps/730/capsule_617x353.jpg"
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")

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
                "text": f"Actualizado: {fecha_actual}",
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
        print(json.dumps(payload, indent=4, ensure_ascii=False))
        return
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code in (200, 204):
        print("Mensaje enviado correctamente.")
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

    if latest_id != last_id or not DISCORD_WEBHOOK_URL:
        send_to_discord(latest_entry)
        if DISCORD_WEBHOOK_URL:
            save_last_id(latest_id)

if __name__ == "__main__":
    main()
