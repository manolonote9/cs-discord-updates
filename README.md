# 🎮 CS2 Update Notifier for Discord

This repository contains an automated Python script that tracks official Counter-Strike 2 updates and sends patch notes directly to a Discord channel via Webhooks.

---

## ✨ Features

- **Automation:** Runs every 30 minutes via GitHub Actions.  
- **Smart Formatting:** Converts Valve's blog HTML into clean, readable Markdown.  
- **Hierarchical Layout:** Supports primary points (•) and sub-points (◦) for clear patch details.  
- **Interactive Design:** Includes a "View Full Notes" link and a themed embed style.  

---

## 🚀 Configuration

### 1️⃣ Prepare the Discord Webhook

1. In your Discord server, go to **Channel Settings → Integrations**.  
2. Create a **New Webhook**, customize the name/avatar, and copy the Webhook URL.  

---

### 2️⃣ Configure Repository Secrets

To ensure the script works securely without exposing your private URL:

1. Go to the **Settings** tab of this repository.  
2. In the side menu, select **Secrets and variables → Actions**.  
3. Click **New repository secret**.  
4. Configure the secret:
   - **Name:** `DISCORD_WEBHOOK`  
   - **Value:** Paste the URL you copied from Discord.  

---

### 3️⃣ Activate Permissions & Actions

1. Go to **Settings → Actions → General**.  
2. Scroll down to **Workflow permissions** and select **Read and write permissions**. Click **Save**.  
3. Go to the **Actions** tab of your repository.  
4. Select the **"Check CS2 Updates"** workflow on the left and click **Run workflow** to test it.  

---

## 🛠️ Project Structure

- `cs2_notifier.py` — Core bot logic (scraping and formatting).  
- `.github/workflows/main.yml` — GitHub Actions configuration.  
- `last_update.txt` — Automatically generated file to track the last patch seen.  

---

Developed with ❤️ for the CS2 community.
