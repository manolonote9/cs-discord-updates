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
# LIMPIEZA Y FORMATO MEJORADO
# ==============================
def clean_html(raw_html):
    """
    Limpia el HTML y aplica formato profesional para Discord.
    """
    if not raw_html:
        return ""
    
    # 1. Eliminar imágenes y elementos que no aportan texto
    text = re.sub(r'<img[^>]*>', '', raw_html)
    text = re.sub(r'<a[^>]*>', '', text)
    text = re.sub(r'</a>', '', text)
    
    # 2. Convertir listas HTML a formato Discord
    text = re.sub(r'<li>(.*?)</li>', r'• \1', text, flags=re.DOTALL)
    text = re.sub(r'<ul>', '', text)
    text = re.sub(r'</ul>', '', text)
    
    # 3. Convertir encabezados a negritas
    text = re.sub(r'<h[1-6]>(.*?)</h[1-6]>', r'**\1**', text, flags=re.DOTALL)
    
    # 4. Convertir párrafos y saltos de línea
    text = re.sub(r'<p>(.*?)</p>', r'\1\n', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    
    # 5. Limpiar etiquetas HTML restantes
    text = re.sub(r'<[^>]+>', '', text)
    
    # 6. Decodificar entidades HTML comunes
    html_entities = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#039;': "'",
        '&nbsp;': ' '
    }
    for entity, char in html_entities.items():
        text = text.replace(entity, char)
    
    # 7. Limpiar líneas vacías y espacios extras
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if line:
            # Detectar secciones importantes
            if line.isupper() or re.match(r'^\[.*\]$', line):
                lines.append(f"\n📌 **{line}**")
            # Detectar posibles cambios/actualizaciones
            elif re.match(r'^[-•*]', line):
                lines.append(line)
            else:
                # Si la línea no tiene formato, agregar bullet point
                lines.append(f"• {line}")
    
    # 8. Unir líneas con saltos apropiados
    formatted_text = '\n'.join(lines)
    
    # 9. Resaltar términos técnicos (IDs, comandos, funciones)
    def highlight_technical(match):
        word = match.group(0)
        # Palabras con guiones bajos, puntos, o mezcla de mayúsculas/minúsculas
        if '_' in word or '.' in word or (any(c.isupper() for c in word[1:]) and word[0].islower()):
            return f'`{word}`'
        return word
    
    formatted_text = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_.]+\b', highlight_technical, formatted_text)
    
    return formatted_text.strip()

def extract_changes(entry):
    """
    Extrae y categoriza los cambios de la actualización.
    """
    content = entry.content[0].value if 'content' in entry else entry.get('summary', '')
    text = clean_html(content)
    
    # Categorías comunes en updates de CS2
    categories = {
        '🎮 **GAMEPLAY**': [],
        '🔧 **MAPAS**': [],
        '🎨 **GRÁFICOS**': [],
        '🐛 **BUG FIXES**': [],
        '⚙️ **MISCELÁNEO**': []
    }
    
    lines = text.split('\n')
    current_category = '⚙️ **MISCELÁNEO**'
    
    for line in lines:
        line_upper = line.upper()
        if 'GAMEPLAY' in line_upper or 'JUEGO' in line_upper:
            current_category = '🎮 **GAMEPLAY**'
        elif 'MAPA' in line_upper or 'MAP' in line_upper:
            current_category = '🔧 **MAPAS**'
        elif 'GRÁFICO' in line_upper or 'GRAPHIC' in line_upper or 'VISUAL' in line_upper:
            current_category = '🎨 **GRÁFICOS**'
        elif 'BUG' in line_upper or 'FIX' in line_upper or 'CORRECCIÓN' in line_upper:
            current_category = '🐛 **BUG FIXES**'
        elif line.startswith('•') or line.startswith('-'):
            categories[current_category].append(line)
    
    # Construir resumen por categorías
    summary = []
    for category, items in categories.items():
        if items:
            summary.append(category)
            summary.extend(items[:5])  # Máximo 5 items por categoría
            if len(items) > 5:
                summary.append(f"  *... y {len(items)-5} cambios más*")
            summary.append("")
    
    return '\n'.join(summary) if summary else text

# ==============================
# CONSTRUCCIÓN DEL EMBED MEJORADO
# ==============================
def build_payload(entry):
    # Extraer fecha del entry
    if hasattr(entry, 'published_parsed'):
        update_date = datetime(*entry.published_parsed[:6])
        date_str = update_date.strftime("%d %b %Y • %H:%M UTC")
    else:
        date_str = datetime.utcnow().strftime("%d %b %Y • %H:%M UTC")
    
    # Obtener cambios formateados
    changes = extract_changes(entry)
    
    # Limitar longitud para Discord
    if len(changes) > 1800:
        changes = changes[:1750] + "...\n\n*La actualización contiene muchos cambios. Haz clic en el botón para verlos todos.*"
    
    # Determinar color basado en tipo de update
    title_lower = entry.title.lower()
    if 'beta' in title_lower:
        embed_color = 10181046  # Púrpura para betas
    elif 'minor' in title_lower or 'pequeña' in title_lower:
        embed_color = 3447003   # Azul para updates menores
    else:
        embed_color = 15844367  # Naranja CS2 para updates principales
    
    payload = {
        "embeds": [{
            "title": f"📢 {entry.title}",
            "description": changes if changes else "No hay descripción detallada disponible.",
            "url": entry.link,
            "color": embed_color,
            "author": {
                "name": "Counter-Strike 2 • Release Notes",
                "icon_url": "https://cms.counter-strike.net/wp-content/uploads/2023/03/cs2_white_logo.png",
                "url": "https://blog.counter-strike.net/"
            },
            "fields": [
                {
                    "name": "📅 Fecha",
                    "value": date_str,
                    "inline": True
                },
                {
                    "name": "🔗 Enlace",
                    "value": "[Notas oficiales]({})".format(entry.link),
                    "inline": True
                },
                {
                    "name": "📊 Tipo",
                    "value": "Actualización Oficial",
                    "inline": True
                }
            ],
            "footer": {
                "text": "CS2 Tracker • Los cambios son automáticos",
                "icon_url": "https://cdn.discordapp.com/embed/avatars/0.png"
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
                        "label": "📖 Ver Notas Completas",
                        "url": entry.link,
                        "emoji": {"name": "🔗"}
                    },
                    {
                        "type": 2,
                        "style": 5,
                        "label": "🌐 Blog Oficial",
                        "url": "https://blog.counter-strike.net/",
                        "emoji": {"name": "📰"}
                    }
                ]
            }
        ]
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

def send_to_discord(webhook_url, payload, max_retries=3):
    """Envía el payload a Discord con reintentos."""
    for attempt in range(max_retries):
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 204:
                return True
            elif response.status_code == 429:  # Rate limit
                retry_after = int(response.headers.get('Retry-After', 5))
                time.sleep(retry_after)
            else:
                print(f"❌ Error Discord: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Intento {attempt + 1} falló: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    return False

def main():
    import time  # Para reintentos
    
    feed = None
    for url in RSS_SOURCES:
        try:
            response = requests.get(
                url, 
                headers={'User-Agent': 'CS2-Update-Bot/1.0'}, 
                timeout=10
            )
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                if feed.entries: 
                    print(f"✅ Feed cargado: {url}")
                    break
        except Exception as e:
            print(f"⚠️ Error con {url}: {e}")
            continue

    if not feed or not feed.entries:
        print("❌ No se pudo obtener ningún feed")
        return

    latest_entry = feed.entries[0]
    latest_id = getattr(latest_entry, 'id', latest_entry.link)
    last_id = get_last_saved_id()

    if latest_id != last_id:
        print(f"📢 Nueva actualización detectada: {latest_entry.title}")
        
        if DISCORD_WEBHOOK_URL:
            payload = build_payload(latest_entry)
            
            # Debug: Guardar payload para revisión
            with open("debug_payload.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            
            if send_to_discord(DISCORD_WEBHOOK_URL, payload):
                save_last_id(latest_id)
                print("✅ Actualización enviada correctamente")
            else:
                print("❌ Error al enviar a Discord")
        else:
            print("⚠️ Configura el DISCORD_WEBHOOK_URL en las variables de entorno")
    else:
        print(f"☕ Sin novedades. Último ID: {last_id}")

if __name__ == "__main__":
    main()
