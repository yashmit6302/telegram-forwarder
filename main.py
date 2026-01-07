import asyncio
import re
import threading
from flask import Flask
from telethon import TelegramClient, events, errors

import os

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")



app = Flask(__name__)

from telethon.sessions import StringSession

client = TelegramClient(
    StringSession(os.environ.get("TG_SESSION")),
    API_ID,
    API_HASH
)


STATE = {
    "source": None,
    "target": None,
    "start_id": None,
    "running": False
}

# ---------------- WEB (Keeps Render alive) ----------------

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# ---------------- UTIL ----------------

def parse_msg_link(link):
    m = re.search(r"t\.me/(?:c/)?([^/]+)/(\d+)", link)
    if not m:
        return None
    chat, msg_id = m.group(1), int(m.group(2))
    if chat.isdigit():
        chat = int("-100" + chat)
    return chat, msg_id

# ---------------- COMMANDS ----------------

@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "🤖 Forwarder Bot Ready\n\n"
        "/set_source\n"
        "/set_target\n"
        "/set_start\n"
        "/run\n"
        "/stop\n"
        "/status"
    )

@client.on(events.NewMessage(pattern="/set_source"))
async def set_source(event):
    try:
        STATE["source"] = event.text.split(maxsplit=1)[1]
        await event.reply("✅ Source set")
    except:
        await event.reply("❌ Usage: /set_source @channel")

@client.on(events.NewMessage(pattern="/set_target"))
async def set_target(event):
    try:
        STATE["target"] = event.text.split(maxsplit=1)[1]
        await event.reply("✅ Target set")
    except:
        await event.reply("❌ Usage: /set_target @channel")

@client.on(events.NewMessage(pattern="/set_start"))
async def set_start(event):
    try:
        _, mid = parse_msg_link(event.text.split(maxsplit=1)[1])
        STATE["start_id"] = mid
        await event.reply(f"✅ Start ID set: {mid}")
    except:
        await event.reply("❌ Invalid link")

@client.on(events.NewMessage(pattern="/status"))
async def status(event):
    await event.reply(
        f"Source: `{STATE['source']}`\n"
        f"Target: `{STATE['target']}`\n"
        f"Start ID: `{STATE['start_id']}`\n"
        f"Running: `{STATE['running']}`"
    )

@client.on(events.NewMessage(pattern="/stop"))
async def stop(event):
    STATE["running"] = False
    await event.reply("🛑 Stopped")

# ---------------- FORWARDING ----------------

@client.on(events.NewMessage(pattern="/run"))
async def run(event):
    if STATE["running"]:
        await event.reply("⚠️ Already running")
        return

    if None in (STATE["source"], STATE["target"], STATE["start_id"]):
        await event.reply("❌ Set source, target & start first")
        return

    STATE["running"] = True
    await event.reply("🚀 Forwarding started")

    source = await client.get_entity(STATE["source"])
    target = await client.get_entity(STATE["target"])
    start_id = STATE["start_id"]

    async for msg in client.iter_messages(
        source,
        reverse=True,
        offset_id=start_id - 1
    ):
        if not STATE["running"]:
            break

        try:
            if not msg.text and not msg.media:
                continue
            await client.forward_messages(target, msg)
            await asyncio.sleep(0.7)
        except errors.FloodWaitError as e:
            await asyncio.sleep(e.seconds + 2)

    STATE["running"] = False
    await event.reply("✅ Done")

# ---------------- START ----------------

async def start_bot():
    await client.connect()
    await client.run_until_disconnected()

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    asyncio.run(start_bot())




