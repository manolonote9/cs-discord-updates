import feedparser
import requests
import os
import re
import json
from datetime import datetime

# Lista de fuentes
RSS_SOURCES = [
    "https://store.steampowered.com/feeds/news/app/730/",
    "https://blog.counter-strike.net/index.php/category/updates/feed/",
    "https://steamcommunity.com/games/730/rss/"
]

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
LAST_UPDATE_FILE = "last_update.txt"

def clean_html(raw_html):
    """Limpia el HTML para que se vea con el formato de las capturas (listas y sub-listas)."""
    cleantext = re.sub(r'<li>\s*<ul>', '<ul>', raw_html) 
    cleantext = re.sub(r'<li>', '• ', cleantext)
    cleantext = re.sub(r'</ul>\s*•', '\n•', cleantext)
    cleantext = re.sub(r'<(b|strong)>', '**', cleantext)
    cleantext = re.sub(r'</(b|strong)>', '**', cleantext)
    cleantext = re.sub(r'<(br|p|/li|/ul|/p)>', '\n', cleantext)
    cleantext = re.sub(r'<.*?>', '', cleantext)
    cleantext = re.sub(r'\n\s*\n', '\n', cleantext)
    
    lines = []
    for line in cleantext.split('\n'):
        if line.strip():
            lines.append(line.strip())
    
    return '\n'.join(lines)

def get_last_saved_id():
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_id(entry_id):
    with open(LAST_UPDATE_FILE, "w") as f:
        f.write(entry_id)

def build_payload(entry):
    """Construye el objeto JSON para Discord."""
    content = ""
    if 'content' in entry:
        content = entry.content[0].value
    else:
        content = entry.get('summary', entry.get('description', ''))
        
    clean_content = clean_html(content)
    
    if len(clean_content) > 2000:
        clean_content = clean_content[:1997] + "..."

    image_url = "https://cdn.akamai.steamstatic.com/steam/apps/730/capsule_617x353.jpg"
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")

    return {
        "username": "Counter-Strike 2 Updates",
        "avatar_url": "https://logodownload.org/wp-content/uploads/2014/11/counter-strike-logo-2.png",
        "embeds": [{
            "title": f"{entry.title}",
            "description": clean_content,
            "url": entry.link,
            "color": 3092790,
            "image": {
                "url": image_url
            },
            "footer": {
                "text": f"Detectado el {fecha_actual} | Valve Official",
                "icon_url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
            }
        }]
    }

def send_to_discord(entry):
    payload = build_payload(entry)
    
    # DEBUG: Imprimir JSON para previsualización externa si no hay URL de Webhook
    if not DISCORD_WEBHOOK_URL:
        print("--- PREVIEW JSON (Copia desde aquí abajo) ---")
        print(json.dumps(payload, indent=4))
        print("--- FIN PREVIEW ---")
        return

    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code == 204:
        print("Mensaje enviado correctamente.")
    else:
        print(f"Error: {response.status_code}")

def main():
    feed = None
    for url in RSS_SOURCES:
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                if feed.entries:
                    break
        except Exception:
            continue

    if not feed or not feed.entries:
        return

    latest_entry = feed.entries[0]
    
    # Si quieres ver la preview sin enviar nada, puedes comentar las líneas de abajo
    # y simplemente llamar a send_to_discord(latest_entry) sin tener el Webhook configurado.
    
    latest_id = getattr(latest_entry, 'id', latest_entry.link)
    last_id = get_last_saved_id()

    if latest_id != last_id or not DISCORD_WEBHOOK_URL:
        send_to_discord(latest_entry)
        if DISCORD_WEBHOOK_URL:
            save_last_id(latest_id)

if __name__ == "__main__":
    main()
