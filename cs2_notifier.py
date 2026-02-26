import feedparser
import requests
import os
import re
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
    """Limpia el HTML para que se vea bien en Discord."""
    # Reemplazar <br> y <li> por saltos de línea
    cleantext = re.sub(r'<(br|li|/li)>', '\n', raw_html)
    # Reemplazar <b> y <strong> por negritas de Markdown
    cleantext = re.sub(r'<(b|strong)>', '**', cleantext)
    cleantext = re.sub(r'</(b|strong)>', '**', cleantext)
    # Eliminar el resto de etiquetas HTML
    cleantext = re.sub(r'<.*?>', '', cleantext)
    # Limpiar espacios y saltos de línea múltiples
    cleantext = re.sub(r'\n\s*\n', '\n', cleantext)
    return cleantext.strip()

def get_last_saved_id():
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_id(entry_id):
    with open(LAST_UPDATE_FILE, "w") as f:
        f.write(entry_id)

def send_to_discord(entry):
    # Extraer y limpiar el contenido de la noticia
    content = entry.get('summary', entry.get('description', ''))
    clean_content = clean_html(content)
    
    # Discord tiene un límite de 4096 caracteres en la descripción, 
    # pero es mejor cortarlo antes para que sea legible (ej. 1500)
    if len(clean_content) > 1500:
        clean_content = clean_content[:1497] + "..."

    image_url = "https://cdn.akamai.steamstatic.com/steam/apps/730/capsule_617x353.jpg"
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")

    payload = {
        "username": "Counter-Strike 2 Updates",
        "avatar_url": "https://logodownload.org/wp-content/uploads/2014/11/counter-strike-logo-2.png",
        "embeds": [{
            "title": f"🛠️ {entry.title}",
            "description": clean_content,
            "url": entry.link,
            "color": 15844367,
            "fields": [
                {
                    "name": "⏰ Detectado el",
                    "value": fecha_actual,
                    "inline": True
                },
                {
                    "name": "🔗 Enlace Original",
                    "value": f"[Ver en el Blog]({entry.link})",
                    "inline": True
                }
            ],
            "image": {
                "url": image_url
            },
            "footer": {
                "text": "Actualización Automática CS2",
                "icon_url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
            }
        }]
    }
    
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code == 204:
        print("Mensaje con notas completas enviado.")
    else:
        print(f"Error: {response.status_code}")

def main():
    if not DISCORD_WEBHOOK_URL:
        print("Error: No DISCORD_WEBHOOK")
        return

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
        print("No se pudieron obtener entradas.")
        return

    latest_entry = feed.entries[0]
    latest_id = getattr(latest_entry, 'id', latest_entry.link)
    last_id = get_last_saved_id()

    if latest_id != last_id:
        send_to_discord(latest_entry)
        save_last_id(latest_id)
    else:
        print("Todo actualizado.")

if __name__ == "__main__":
    main()
