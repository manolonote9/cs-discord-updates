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

# URL estable del logo de CS2 para el avatar del bot
CS2_LOGO_URL = "https://raw.githubusercontent.com/SteamDatabase/GameTracking-CS2/master/game/core/pak01_dir/resource/flash/econ/tournaments/logos/csgo.png"

def clean_html(raw_html):
    """Limpia el HTML mejorando el espaciado para mayor legibilidad."""
    # 1. Formatear listas y añadir un salto de línea extra para separación
    cleantext = re.sub(r'<li>\s*<ul>', '<ul>', raw_html) 
    cleantext = re.sub(r'<li>', '\n• ', cleantext) # Salto de línea antes de cada punto
    
    # 2. Resaltar secciones entre corchetes (ej: [ MISC ])
    cleantext = re.sub(r'\[(.*?)\]', r'\n**[ \1 ]**', cleantext)
    
    # 3. Negritas
    cleantext = re.sub(r'<(b|strong)>', '**', cleantext)
    cleantext = re.sub(r'</(b|strong)>', '**', cleantext)
    
    # 4. Saltos de línea generales
    cleantext = re.sub(r'<(br|p|/li|/ul|/p)>', '\n', cleantext)
    
    # 5. Limpiar etiquetas restantes
    cleantext = re.sub(r'<.*?>', '', cleantext)
    
    # 6. Post-procesado de líneas para espaciado "aireado"
    lines = []
    for line in cleantext.split('\n'):
        stripped = line.strip()
        if stripped:
            lines.append(stripped + "\n") 
    
    return '\n'.join(lines).strip()

def get_last_saved_id():
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_id(entry_id):
    with open(LAST_UPDATE_FILE, "w") as f:
        f.write(entry_id)

def build_payload(entry):
    """Construye el payload con el botón de View y espaciado mejorado."""
    content = ""
    if 'content' in entry:
        content = entry.content[0].value
    else:
        content = entry.get('summary', entry.get('description', ''))
        
    clean_content = clean_html(content)
    
    if len(clean_content) > 1800:
        clean_content = clean_content[:1797] + "..."

    # Imagen de cabecera (banner)
    image_url = "https://cdn.akamai.steamstatic.com/steam/apps/730/capsule_617x353.jpg"
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Estructura del mensaje de Discord
    return {
        "embeds": [{
            "title": f"✨ {entry.title}",
            "description": clean_content + "\n\n**━━━━━━━━━━━━━━━━━━━━━━━**",
            "url": entry.link,
            "color": 3092790,
            "fields": [
                {
                    "name": "\u200b", 
                    "value": f"**[View ↗️]({entry.link})**",
                    "inline": False
                }
            ],
            "image": {
                "url": image_url
            },
            "footer": {
                "text": f"Actualizado: {fecha_actual}",
                "icon_url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
            }
        }]
    }

def send_to_discord(entry):
    payload = build_payload(entry)
    
    if not DISCORD_WEBHOOK_URL:
        print(json.dumps(payload, indent=4))
        return

    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code == 204:
        print("Mensaje elegante enviado.")
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
    latest_id = getattr(latest_entry, 'id', latest_entry.link)
    last_id = get_last_saved_id()

    # Siempre forzamos el envío si no hay Webhook para ver el JSON en los logs
    if latest_id != last_id or not DISCORD_WEBHOOK_URL:
        send_to_discord(latest_entry)
        if DISCORD_WEBHOOK_URL:
            save_last_id(latest_id)

if __name__ == "__main__":
    main()
