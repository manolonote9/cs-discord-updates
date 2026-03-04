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

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK", "") 
LAST_UPDATE_FILE = "last_update.txt"

# ==============================
# LIMPIEZA Y FORMATO (ESTILO LISTA)
# ==============================
def clean_html(raw_html):
    """
    Limpia el HTML y formatea como lista de guiones para Discord.
    """
    # 1. Eliminar etiquetas de imagen o enlaces complejos antes de procesar texto
    text = re.sub(r'<img.*?>', '', raw_html)
    
    # 2. Convertir <li> a guiones de lista de Discord
    text = re.sub(r'<li>(.*?)</li>', r'- \1', text, flags=re.DOTALL)
    
    # 3. Limpieza general de etiquetas HTML
    text = re.sub(r'<(br|p|/ul|/p)>', '\n', text)
    text = re.sub(r'<.*?>', '', text)

    # 4. Formatear encabezados [ SECCION ]
    text = re.sub(r'(\[?\s?[A-Z]{3,}\s?\]?:?)', r'\n**\1**', text)

    # 5. Procesar línea por línea
    final_lines = []
    for line in text.split('\n'):
        clean_line = line.strip()
        if not clean_line:
            continue
            
        # Eliminar comas sueltas al final (común en feeds de Steam)
        clean_line = re.sub(r',$', '', clean_line)

        # Si la línea no es un encabezado y no empieza por guion, ponle uno
        if not clean_line.startswith('**') and not clean_line.startswith('-'):
            clean_line = f"- {clean_line}"
        
        final_lines.append(clean_line)

    result = '\n'.join(final_lines)

    # 6. Resaltar términos técnicos (IDs, comandos, funciones)
    def protect_identifiers(match):
        token = match.group(0)
        if "_" in token or "." in token or (any(c.isupper() for c in token[1:]) and token[0].isupper()):
            return f"`{token}`"
        return token

    result = re.sub(r'\b[A-Za-z_][A-Za-z0-9_.]+\b', protect_identifiers, result)
    return result

# ==============================
# CONSTRUCCIÓN DEL EMBED
# ==============================
def build_payload(entry):
    content = entry.content[0].value if 'content' in entry else entry.get('summary', '')
    clean_content = clean_html(content)

    # Recorte de seguridad para Discord
    if len(clean_content) > 1500:
        clean_content = clean_content[:1490] + "...\n\n*Pulsa el botón para ver todo.*"

    payload = {
        "embeds": [{
            "title": f"📝 {entry.title}",
            "description": clean_content,
            "url": entry.link,
            "color": 15844367, # Naranja CS2
            "author": {
                "name": "Counter-Strike 2 Update",
                "icon_url": "https://cms.counter-strike.net/wp-content/uploads/2023/03/cs2_white_logo.png"
            },
            "footer": {"text": "Valve Corp • Release Notes"},
            "timestamp": datetime.utcnow().isoformat()
        }],
        "components": [{
            "type": 1,
            "components": [{
                "type": 2,
                "style": 5,
                "label": "Ver Notas Completas",
                "url": entry.link,
                "emoji": {"name": "🔗"}
            }]
        }]
    }
    return payload

# ==============================
# LÓGICA DE ENVÍO Y PERSISTENCIA
# ==============================
def get_last_saved_id():
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def save_last_id(entry_id):
    with open(LAST_UPDATE_FILE, "w", encoding="utf-8") as f:
        f.write(entry_id)

def main():
    feed = None
    for url in RSS_SOURCES:
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                if feed.entries: break
        except: continue

    if not feed or not feed.entries: return

    latest_entry = feed.entries[0]
    latest_id = getattr(latest_entry, 'id', latest_entry.link)
    last_id = get_last_saved_id()

    if latest_id != last_id:
        if DISCORD_WEBHOOK_URL:
            requests.post(DISCORD_WEBHOOK_URL, json=build_payload(latest_entry))
            save_last_id(latest_id)
            print("✅ Actualización enviada.")
        else:
            print("⚠️ Configura el DISCORD_WEBHOOK_URL.")
    else:
        print("☕ Sin novedades.")

if __name__ == "__main__":
    main()
