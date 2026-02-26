import feedparser
import requests
import os
import json

# Configuración
RSS_URL = "https://blog.counter-strike.net/index.php/category/updates/feed/"
# El Webhook se lee desde las variables de entorno de GitHub para mayor seguridad
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

    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        print("No se pudieron obtener entradas del RSS.")
        return

    latest_entry = feed.entries[0]
    latest_id = latest_entry.id
    
    last_id = get_last_saved_id()

    if latest_id != last_id:
        print(f"Nueva actualización detectada: {latest_entry.title}")
        send_to_discord(latest_entry)
        save_last_id(latest_id)
    else:
        print("No hay actualizaciones nuevas.")

if __name__ == "__main__":
    main()