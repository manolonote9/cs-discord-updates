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
    """Limpia el HTML eliminando caracteres innecesarios y corrigiendo sub-puntos."""
    
    # 1. Identificar sub-puntos antes de limpiar etiquetas
    # Buscamos específicamente la estructura de listas anidadas de Steam/Valve
    cleantext = re.sub(r'<ul>\s*<li>', '<ul><subli>', raw_html)
    cleantext = re.sub(r'</li>\s*<li>', '</li><subli>', cleantext)
    
    # 2. Formatear puntos principales y sub-puntos con el estilo solicitado
    cleantext = re.sub(r'<li>', '\n• ', cleantext)
    cleantext = re.sub(r'<subli>', '\n　　◦ ', cleantext)
    
    # 3. Formatear secciones [ TITULO ]
    cleantext = re.sub(r'\[(.*?)\]', r'\n**[ \1 ]**', cleantext)
    
    # 4. Negritas
    cleantext = re.sub(r'<(b|strong)>', '**', cleantext)
    cleantext = re.sub(r'</(b|strong)>', '**', cleantext)
    
    # 5. Saltos de línea y limpieza de etiquetas
    cleantext = re.sub(r'<(br|p|/li|/ul|/p)>', '\n', cleantext)
    cleantext = re.sub(r'<.*?>', '', cleantext)
    
    # 6. Post-procesado para eliminar "\" y mejorar el aireado
    final_lines = []
    # Eliminamos el caracter \ si aparece suelto como separador
    cleantext = cleantext.replace('\\', '')
    
    lines = cleantext.split('\n')
    for line in lines:
        content = line.strip()
        if content:
            # Si es un encabezado o punto principal, añadimos espacio arriba para que respire
            if content.startswith('**[') or content.startswith('•'):
                final_lines.append("\n" + content)
            else:
                # Mantenemos la línea tal cual para los sub-puntos (con su indentación)
                final_lines.append(line)
    
    return '\n'.join(final_lines).strip()

def get_last_saved_id():
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_id(entry_id):
    with open(LAST_UPDATE_FILE, "w") as f:
        f.write(entry_id)

def build_payload(entry):
    """Construye el payload para Discord con formato limpio."""
    content = ""
    if 'content' in entry:
        content = entry.content[0].value
    else:
        content = entry.get('summary', entry.get('description', ''))
        
    clean_content = clean_html(content)
    
    if len(clean_content) > 3500:
        clean_content = clean_content[:3497] + "..."

    image_url = "https://cdn.akamai.steamstatic.com/steam/apps/730/capsule_617x353.jpg"
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")

    return {
        "embeds": [{
            "title": f"✨ {entry.title}",
            "description": clean_content + "\n\n**━━━━━━━━━━━━━━━━━━━━━━━**",
            "url": entry.link,
            "color": 3092790,
            "fields": [
                {
                    "name": "\u200b", 
                    "value": f"**[View Full Notes ↗️]({entry.link})**",
                    "inline": False
                }
            ],
            "image": {
                "url": image_url
            },
            "footer": {
                "text": f"Actualizado: {fecha_actual}",
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

    if latest_id != last_id or not DISCORD_WEBHOOK_URL:
        send_to_discord(latest_entry)
        if DISCORD_WEBHOOK_URL:
            save_last_id(latest_id)

if __name__ == "__main__":
    main()
