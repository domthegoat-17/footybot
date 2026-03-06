import os
import requests

def post_to_discord(content: str, username: str = "FootyBot"):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("Missing DISCORD_WEBHOOK_URL environment variable.")

    # Discord message limit is 2000 characters
    chunks = []
    text = content.strip()
    while len(text) > 2000:
        chunks.append(text[:2000])
        text = text[2000:]
    if text:
        chunks.append(text)

    for i, chunk in enumerate(chunks, start=1):
        payload = {
            "username": username,
            "content": chunk if len(chunks) == 1 else f"(Part {i}/{len(chunks)})\n{chunk}",
        }
        r = requests.post(webhook_url, json=payload, timeout=15)
        if r.status_code not in (200, 204):
            raise RuntimeError(f"Discord webhook failed: {r.status_code} {r.text}")