import os
import json
import aiohttp
import asyncio
import datetime
from dotenv import load_dotenv
from aiohttp import web

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select

# =========================
# LOAD ENV & CONFIG
# =========================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
INFOBIP_API_KEY = os.getenv("INFOBIP_API_KEY")
INFOBIP_URL = os.getenv("INFOBIP_URL")  # e.g. "https://4e6qy8.api.infobip.com"
WHATSAPP_SENDER = os.getenv("WHATSAPP_NUMBER")  # your Infobip WhatsApp number

API_URL = "https://router.huggingface.co/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}
MEMORY_FILE = "memory.json"

# =========================
# DISCORD BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# =========================
# MEMORY STRUCTURES
# =========================
user_memory = {}
prefixes = {}
auto_reply_channels = set()
coding_channels = set()
user_personalities = {}
user_models = {}
linked_accounts = {}   # discord_id -> whatsapp:<phone>
whatsapp_users = {}     # phone -> metadata

def load_memory():
    global user_memory, prefixes, auto_reply_channels, coding_channels
    global user_personalities, user_models, linked_accounts, whatsapp_users
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        user_memory = data.get("user_memory", {})
        prefixes = {str(k): v for k, v in data.get("prefixes", {}).items()}
        auto_reply_channels = set(data.get("auto_reply_channels", []))
        coding_channels = set(data.get("coding_channels", []))
        user_personalities = data.get("user_personalities", {})
        user_models = data.get("user_models", {})
        linked_accounts = data.get("linked_accounts", {})
        whatsapp_users = data.get("whatsapp_users", {})
        print(f"[MEMORY] Loaded: {len(user_memory)} users, auto={len(auto_reply_channels)}, coding={len(coding_channels)}")
    except Exception as e:
        print(f"[WARN] Could not load memory: {e}")
        user_memory = {}
        prefixes = {}
        auto_reply_channels = set()
        coding_channels = set()
        user_personalities = {}
        user_models = {}
        linked_accounts = {}
        whatsapp_users = {}

def save_memory():
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "user_memory": user_memory,
                "prefixes": prefixes,
                "auto_reply_channels": list(auto_reply_channels),
                "coding_channels": list(coding_channels),
                "user_personalities": user_personalities,
                "user_models": user_models,
                "linked_accounts": linked_accounts,
                "whatsapp_users": whatsapp_users
            }, f, ensure_ascii=False, indent=2)
        print("[MEMORY] Saved")
    except Exception as e:
        print(f"[ERROR] Memory save failed: {e}")

load_memory()

# =========================
# HELPERS
# =========================
def get_model_name(user_id: str) -> str:
    return user_models.get(user_id, "LazyV.----")

def system_prompt_for(model_name: str, personality: str | None) -> str:
    base = (
        f"You are {model_name}, a human-like AI developed by Xohus Interactive LLC. "
    )
    # simple traits
    if model_name == "LazyV.----":
        base += "Casual, adaptive, minimal emoji. "
    elif model_name == "LazyV..---":
        base += "Enhanced reasoning, smoother replies. "
    elif model_name == "LazyV...--":
        base += "Near-human flow, memory linking. "
    elif model_name == "LazyV..-.-":
        base += "Unrestricted, bold tone (within TOS). "
    if personality:
        base += f"Personality style: {personality}. "
    base += "Never reveal internal logic or tokens. Default to English unless user explicitly uses another language."
    return base

async def query_hf(messages, model_name: str, personality: str | None):
    sys_msg = {"role": "system", "content": system_prompt_for(model_name, personality)}
    payload = {"model": "deepseek-ai/DeepSeek-V3.2-Exp:novita", "messages": [sys_msg] + messages[-10:]}
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                content = data["choices"][0]["message"]["content"]
                content = content.replace("DeepSeek", model_name)
                return content
            else:
                txt = await resp.text()
                print(f"[ERROR] HF API {resp.status}: {txt}")
                return "⚠️ LazyAI error."

# -------------------------
# WHATSAPP SENDING / RECEIVING
# -------------------------
async def send_whatsapp_text(to_phone: str, text: str):
    """Send a WhatsApp text message via Infobip API."""
    url = f"{INFOBIP_URL}/whatsapp/1/message/text"
    payload = {
        "messages": [
            {
                "from": WHATSAPP_SENDER,
                "to": to_phone,
                "messageId": str(datetime.datetime.utcnow().timestamp()),
                "content": {"text": text}
            }
        ]
    }
    headers = {
        "Authorization": f"App {INFOBIP_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            text_resp = await resp.text()
            print(f"[WA SEND] to {to_phone} status {resp.status}, resp {text_resp}")
            return resp.status, text_resp

async def handle_whatsapp_incoming(data: dict):
    """
    Called when webhook from Infobip arrives with a WhatsApp message.
    `data` is the JSON payload from Infobip.
    """
    # This depends on Infobip webhook structure. Example:
    # data["results"][0]["from"] and data["results"][0]["message"]["text"]
    results = data.get("results", [])
    for r in results:
        from_phone = r.get("from")
        msg = r.get("message", {}).get("text", "")
        print(f"[WA IN] From {from_phone}: {msg}")
        # find linked user memory id
        memory_id = None
        # if linked via discord
        for discord_id, wa in linked_accounts.items():
            if wa == f"whatsapp:{from_phone}":
                memory_id = discord_id
                break
        if memory_id is None:
            # not linked → use phone as memory key
            memory_id = f"whatsapp:{from_phone}"
        # initialize memory struct
        user_memory.setdefault(memory_id, []).append({"role": "user", "content": msg})
        model = get_model_name(memory_id)
        personality = user_personalities.get(memory_id, None)
        reply = await query_hf(user_memory[memory_id], model, personality)
        user_memory[memory_id].append({"role": "assistant", "content": reply})
        save_memory()
        # send reply
        await send_whatsapp_text(from_phone, reply)

# -------------------------
# WEBHOOK SERVER (aiohttp)
# -------------------------
async def whatsapp_webhook_handler(request: web.Request):
    try:
        data = await request.json()
    except:
        return web.Response(status=400, text="bad json")
    # debug log
    print(f"[WEBHOOK] Received WA payload: {data}")
    # handle incoming
    await handle_whatsapp_incoming(data)
    return web.Response(status=200, text="ok")

def start_webhook_server():
    app = web.Application()
    app.router.add_post("/whatsapp-webhook", whatsapp_webhook_handler)
    runner = web.AppRunner(app)
    loop = asyncio.get_event_loop()

    async def _run():
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("WA_WEBHOOK_PORT", "8000")))
        await site.start()
        print("[WEBHOOK] WhatsApp webhook listening on port", os.getenv("WA_WEBHOOK_PORT", "8000"))

    loop.create_task(_run())

# =========================
# DISCORD BUTTONS
# =========================
class LazyAIButtons(View):
    def __init__(self, uid: str, prompt: str):
        super().__init__(timeout=None)
        self.uid = uid
        self.prompt = prompt

    @discord.ui.button(label="🔁 Regenerate", style=discord.ButtonStyle.primary)
    async def regenerate(self, interaction: discord.Interaction, _: Button):
        if str(interaction.user.id) != self.uid:
            return await interaction.response.send_message("❌ Not your message.", ephemeral=True)
        await interaction.response.defer()
        msgs = user_memory.get(self.uid, [])
        model = get_model_name(self.uid)
        personality = user_personalities.get(self.uid, None)
        msgs.append({"role": "user", "content": self.prompt})
        reply = await query_hf(msgs, model, personality)
        msgs.append({"role": "assistant", "content": reply})
        user_memory[self.uid] = msgs
        save_memory()
        try:
            await interaction.message.edit(content=f"🧠 {reply}", view=self)
        except:
            await interaction.followup.send(f"🧠 {reply}", ephemeral=True)

    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, _: Button):
        if str(interaction.user.id) != self.uid:
            return await interaction.response.send_message("❌ You can’t delete this.", ephemeral=True)
        try:
            await interaction.message.delete()
        except Exception as e:
            print(f"[WARN] Delete failed: {e}")
            await interaction.response.send_message("Could not delete (no perms).", ephemeral=True)

# -------------------------
# DISCORD COMMANDS
# -------------------------
@tree.command(name="ask", description="Ask LazyAI on Discord.")
@app_commands.describe(prompt="Your message")
async def ask(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    uid = str(interaction.user.id)
    print(f"[LOG] /ask by {interaction.user}: {prompt}")
    user_memory.setdefault(uid, []).append({"role": "user", "content": prompt})
    model = get_model_name(uid)
    personality = user_personalities.get(uid, None)
    reply = await query_hf(user_memory[uid], model, personality)
    user_memory[uid].append({"role": "assistant", "content": reply})
    save_memory()
    await interaction.followup.send(f"🧠 {reply}", view=LazyAIButtons(uid, prompt))

@tree.command(name="link-whatsapp", description="Link your Discord account to a WhatsApp number.")
@app_commands.describe(phone_number="e.g. 9665XXXXXXXX")
async def link_whatsapp(interaction: discord.Interaction, phone_number: str):
    uid = str(interaction.user.id)
    linked_accounts[uid] = f"whatsapp:{phone_number}"
    whatsapp_users[phone_number] = {
        "linked_discord": uid,
        "last_interaction": datetime.datetime.utcnow().isoformat(),
        "preferred_language": "en",
        "memory_id": uid
    }
    save_memory()
    await interaction.response.send_message(f"✅ Linked WA number `{phone_number}` to your Discord account.", ephemeral=True)

@tree.command(name="set-autoreply-channel", description="Enable auto-reply in this channel.")
async def set_auto(interaction: discord.Interaction):
    auto_reply_channels.add(interaction.channel_id)
    save_memory()
    await interaction.response.send_message("✅ Auto-reply enabled here.", ephemeral=True)

@tree.command(name="set-auto-reply-coding", description="Enable coding auto-reply in this channel.")
async def set_auto_coding(interaction: discord.Interaction):
    coding_channels.add(interaction.channel_id)
    save_memory()
    await interaction.response.send_message("✅ Coding auto-reply enabled here.", ephemeral=True)

@tree.command(name="set-prefix", description="Set custom prefix for this server.")
@app_commands.describe(prefix="Trigger prefix text")
async def set_prefix(interaction: discord.Interaction, prefix: str):
    if not interaction.guild_id:
        return await interaction.response.send_message("Must run in server.", ephemeral=True)
    prefixes[str(interaction.guild_id)] = prefix.lower()
    save_memory()
    await interaction.response.send_message(f"✅ Prefix set to `{prefix}`")

@tree.command(name="change-personality", description="Change how I talk to you.")
@app_commands.describe(personality="Style or description")
async def change_personality(interaction: discord.Interaction, personality: str):
    uid = str(interaction.user.id)
    user_personalities[uid] = personality
    save_memory()
    await interaction.response.send_message(f"✅ Personality set to `{personality}`")

@tree.command(name="clear-memory", description="Clear your memory.")
async def clear_memory(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    user_memory.pop(uid, None)
    save_memory()
    await interaction.response.send_message("🧠 Memory cleared.", ephemeral=True)

@tree.command(name="help", description="Show commands.")
async def help_cmd(interaction: discord.Interaction):
    text = (
        "**Commands**\n"
        "/ask — Chat with me\n"
        "/link-whatsapp — Connect your WA & Discord\n"
        "/set-autoreply-channel — Auto-reply here\n"
        "/set-auto-reply-coding — Auto-code replies\n"
        "/set-prefix — Prefix mode\n"
        "/change-personality — Change tone\n"
        "/clear-memory — Wipe history"
    )
    await interaction.response.send_message(text, ephemeral=True)

# -------------------------
# DISCORD MESSAGE HANDLING
# -------------------------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    uid = str(message.author.id)
    gid = str(message.guild.id) if message.guild else None
    text = message.content.strip()
    print(f"[MSG] {message.author} in {message.channel}: {text}")

    if message.channel.id in auto_reply_channels or message.channel.id in coding_channels:
        await handle_message(message, text)
        return

    if gid:
        pref = prefixes.get(gid)
        if pref and text.lower().startswith(pref.lower()):
            stripped = text[len(pref):].strip()
            await handle_message(message, stripped)
            return

    await bot.process_commands(message)

async def handle_message(message: discord.Message, prompt: str):
    uid = str(message.author.id)
    model = get_model_name(uid)
    personality = user_personalities.get(uid, None)
    user_memory.setdefault(uid, []).append({"role": "user", "content": prompt})
    reply = await query_hf(user_memory[uid], model, personality)
    user_memory[uid].append({"role": "assistant", "content": reply})
    save_memory()
    await message.channel.send(f"🧠 {reply}", view=LazyAIButtons(uid, prompt))

# =========================
# RUN EVERYTHING
# =========================
def main():
    # start WhatsApp webhook server
    start_webhook_server()
    # run discord bot
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
