import feedparser
import requests
import os
import json

# Lista de fuentes (por si una falla)
RSS_SOURCES = [
    "https://store.steampowered.com/feeds/news/app/730/",
    "https://blog.counter-strike.net/index.php/category/updates/feed/",
    "https://steamcommunity.com/games/730/rss/"
]

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
LAST_UPDATE_FILE = "last_update.txt"

def get_last_saved_id():
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_id(entry_id):
    with open(LAST_UPDATE_FILE, "w") as f:
        f.write(entry_id)

def send_to_discord(entry):
    payload = {
        "username": "CS2 Updates",
        "avatar_url": "https://logodownload.org/wp-content/uploads/2014/11/counter-strike-logo-2.png",
        "embeds": [{
            "title": "🚀 Nueva Actualización: " + entry.title,
            "description": "Se han publicado nuevas notas de parche para Counter-Strike 2.",
            "url": entry.link,
            "color": 15844367,
            "footer": {
                "text": "Valve Official Blog | GitHub Action Bot"
            }
        }]
    }
    
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code == 204:
        print("Notificación enviada con éxito a Discord.")
    else:
        print(f"Error enviando a Discord: {response.status_code}")

def main():
    if not DISCORD_WEBHOOK_URL:
        print("Error: No se ha configurado la variable DISCORD_WEBHOOK.")
        return

    feed = None
    # Intentamos obtener datos de las fuentes disponibles
    for url in RSS_SOURCES:
        try:
            # Usamos un User-Agent para evitar bloqueos de Valve/Steam
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                if feed.entries:
                    print(f"Datos obtenidos exitosamente de: {url}")
                    break
        except Exception as e:
            print(f"Error al conectar con {url}: {e}")
            continue

    if not feed or not feed.entries:
        print("No se pudieron obtener entradas de ninguna fuente RSS.")
        return

    latest_entry = feed.entries[0]
    # Usamos el link como ID si el ID no está disponible
    latest_id = getattr(latest_entry, 'id', latest_entry.link)
    
    last_id = get_last_saved_id()

    if latest_id != last_id:
        print(f"Nueva actualización detectada: {latest_entry.title}")
        send_to_discord(latest_entry)
        save_last_id(latest_id)
    else:
        print("No hay actualizaciones nuevas.")

if __name__ == "__main__":
    main()
