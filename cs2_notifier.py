import feedparser
import requests
import os
import re
import json
from datetime import datetime

# ==============================
# CONFIGURACIÓN
# ==============================
RSS_SOURCES = [
    "https://store.steampowered.com/feeds/news/app/730/",
    "https://blog.counter-strike.net/index.php/category/updates/feed/",
    "https://steamcommunity.com/games/730/rss/"
]

# Si no usas variable de entorno, pega tu URL aquí entre las comillas
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK", "") 
LAST_UPDATE_FILE = "last_update.txt"

# ==============================
# LIMPIEZA Y FORMATO (MARKDOWN)
# ==============================
def clean_html(raw_html):
    """
    Limpia el HTML de Steam y aplica formato Markdown de Discord.
    """
    # 1. Manejo de listas anidadas
    def parse_list(html):
        def sub_list(match):
            sub = match.group(1)
            # Sub-items (círculo hueco)
            sub = re.sub(r'<li>(.*?)</li>', r'　　◦ \1', sub, flags=re.DOTALL)
            return sub
        
        # Primero procesa listas internas
        html = re.sub(r'<ul>(.*?)</ul>', sub_list, html, flags=re.DOTALL)
        # Luego lista principal (punto sólido)
        html = re.sub(r'<li>(.*?)</li>', r'• \1', html, flags=re.DOTALL)
        return html

    cleantext = parse_list(raw_html)

    # 2. Eliminar etiquetas HTML restantes y normalizar saltos
    cleantext = re.sub(r'<(br|p|/li|/ul|/p)>', '\n', cleantext)
    cleantext = re.sub(r'<.*?>', '', cleantext)
    
    # 3. Formateo de Secciones (Pone en negrita [ MAPS ], GAMEPLAY:, etc.)
    cleantext = re.sub(r'(\[?\s?[A-Z]{3,}\s?\]?:?)', r'**\1**', cleantext)

    # 4. Limpieza de líneas vacías
    lines = [line.strip() for line in cleantext.split('\n') if line.strip()]
    result = '\n'.join(lines)

    # 5. Proteger identificadores técnicos (versiones, archivos, comandos)
    def protect_identifiers(match):
        token = match.group(0)
        # Si tiene _, . o CamelCase, se envuelve en bloque de código `text`
        if "_" in token or "." in token or (any(c.isupper() for c in token[1:]) and token[0].isupper()):
            return f"`{token}`"
        return token

    result = re.sub(r'\b[A-Za-z_][A-Za-z0-9_.]+\b', protect_identifiers, result)
    return result

# ==============================
# PERSISTENCIA
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
# CONSTRUCCIÓN DEL EMBED
# ==============================
def build_payload(entry):
    content = ""
    if 'content' in entry:
        content = entry.content[0].value
    else:
        content = entry.get('summary', entry.get('description', ''))

    clean_content = clean_html(content)

    # Límite visual: si es muy largo, recortamos para no saturar Discord
    if len(clean_content) > 1200:
        clean_content = clean_content[:1190] + "...\n\n*(Notas truncadas para mayor brevedad)*"

    # Estética CS2
    image_url = "https://cdn.akamai.steamstatic.com/steam/apps/730/capsule_617x353.jpg"
    cs_orange = 15844367 

    payload = {
        "embeds": [{
            "title": f"🛠️ {entry.title}",
            "description": f"{clean_content}\n\n**━━━━━━━━━━━━━━━━━━━━━━━**",
            "url": entry.link,
            "color": cs_orange,
            "author": {
                "name": "Counter-Strike 2 Update",
                "icon_url": "https://cms.counter-strike.net/wp-content/uploads/2023/03/cs2_white_logo.png"
            },
            "image": {
                "url": image_url
            },
            "footer": {
                "text": "Valve Corporation • Notas de Lanzamiento",
            },
            "timestamp": datetime.utcnow().isoformat()
        }],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "label": "Leer notas completas 🌐",
                        "url": entry.link
                    }
                ]
            }
        ]
    }

    return payload

# ==============================
# ENVÍO Y EJECUCIÓN
# ==============================
def send_to_discord(entry):
    payload = build_payload(entry)
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ No hay Webhook configurado. Previsualización del JSON:")
        print(json.dumps(payload, indent=4, ensure_ascii=False))
        return

    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code in (200, 204):
        print("✅ Mensaje enviado a Discord con éxito.")
    else:
        print(f"❌ Error {response.status_code}: {response.text}")

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
        except Exception as e:
            print(f"Error accediendo a {url}: {e}")
            continue

    if not feed or not feed.entries:
        print("No se pudieron obtener entradas de los feeds.")
        return

    latest_entry = feed.entries[0]
    # Usar ID o link como identificador único
    latest_id = getattr(latest_entry, 'id', latest_entry.link)
    last_id = get_last_saved_id()

    # Si es noticia nueva o si no hay Webhook (para pruebas)
    if latest_id != last_id:
        send_to_discord(latest_entry)
        if DISCORD_WEBHOOK_URL:
            save_last_id(latest_id)
    else:
        print("☕ No hay actualizaciones nuevas por ahora.")

if __name__ == "__main__":
    main()
