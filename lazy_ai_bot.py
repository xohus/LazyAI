# lazy_ai_bot.py

import discord
from discord import app_commands
from discord.ext import commands
import os, aiohttp, io, shutil, json, base64
from dotenv import load_dotenv
from langdetect import detect
from discord.ui import View, Button

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# ==== ROUTER MODEL ENDPOINTS ====
CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_NAME = "deepseek-ai/DeepSeek-V3.2-Exp:novita"
IMAGE_URL = "https://router.huggingface.co/models/stabilityai/stable-diffusion-2"
TTS_URL = "https://router.huggingface.co/models/suno/bark"
SPEECH_TO_TEXT_URL = "https://router.huggingface.co/models/openai/whisper"

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

MEMORY_FILE = "memory.json"
user_memory = {}
prefixes = {}
auto_reply_channels = set()
personalities = {}

def load_memory():
    global user_memory, prefixes, auto_reply_channels, personalities
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        user_memory = data.get("user_memory", {})
        prefixes = data.get("prefixes", {})
        auto_reply_channels = set(data.get("auto_reply_channels", []))
        personalities = data.get("personalities", {})
        print("[DEBUG] Memory loaded.")
    except Exception as e:
        print(f"[ERROR] Memory load failed: {e}")
        user_memory = {}
        prefixes = {}
        auto_reply_channels = set()
        personalities = {}

def save_memory():
    data = {
        "user_memory": user_memory,
        "prefixes": prefixes,
        "auto_reply_channels": list(auto_reply_channels),
        "personalities": personalities
    }
    tmp = MEMORY_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        shutil.move(tmp, MEMORY_FILE)
        print("[DEBUG] Memory saved.")
    except Exception as e:
        print(f"[ERROR] Save failed: {e}")

load_memory()

def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

async def query_hf(messages):
    payload = {"model": MODEL_NAME, "messages": messages}
    async with aiohttp.ClientSession() as session:
        async with session.post(CHAT_URL, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                content = data["choices"][0]["message"]["content"]
                return content.replace("DeepSeek", "LazyAI")
            else:
                err = await resp.text()
                print(f"[ERROR] query_hf {resp.status}: {err}")
                return "⚠️ LazyAI is offline or sleepy."

async def generate_image(prompt):
    async with aiohttp.ClientSession() as session:
        async with session.post(IMAGE_URL, headers=HEADERS, json={"inputs": prompt}) as resp:
            return await resp.read() if resp.status == 200 else None

async def text_to_speech(text):
    async with aiohttp.ClientSession() as session:
        async with session.post(TTS_URL, headers=HEADERS, json={"inputs": text}) as resp:
            return await resp.read() if resp.status == 200 else None

async def speech_to_text(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    async with aiohttp.ClientSession() as session:
        async with session.post(SPEECH_TO_TEXT_URL, headers=HEADERS, json={"inputs": b64}) as resp:
            if resp.status == 200:
                return (await resp.json()).get("text", "")
            return ""

async def web_search(query):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.duckduckgo.com/", params={"q": query, "format": "json"}) as resp:
            data = await resp.json()
            return data.get("AbstractText", "🔍 No info found.")

class LazyResponseActions(View):
    def __init__(self, prompt, user_id, snapshot):
        super().__init__(timeout=None)
        self.prompt = prompt
        self.user_id = user_id
        self.snapshot = snapshot

    @discord.ui.button(label="🔄 Regenerate", style=discord.ButtonStyle.primary)
    async def regenerate(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ Not your button!", ephemeral=True)
        await interaction.response.defer()
        msgs = list(self.snapshot)
        msgs.append({"role": "user", "content": self.prompt})
        reply = await query_hf(msgs)
        await interaction.followup.send(f"🧠 {reply}", view=LazyResponseActions(self.prompt, self.user_id, msgs))

    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ Not your message.", ephemeral=True)
        await interaction.message.delete()

@bot.event
async def on_ready():
    print(f"🧠 LazyAI is online as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"[DEBUG] Synced {len(synced)} commands.")
    except Exception as e:
        print(f"[ERROR] Sync failed: {e}")

@tree.command(name="ask", description="Ask LazyAI anything")
@app_commands.describe(prompt="What do you want to ask?")
async def ask(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    uid = str(interaction.user.id)
    user_memory.setdefault(uid, [])
    personality = personalities.get(uid)
    messages = []
    if personality:
        messages.append({"role": "system", "content": f"Adopt this personality: {personality}"})
    messages += user_memory[uid][-10:] + [{"role": "user", "content": prompt}]
    reply = await query_hf(messages)
    user_memory[uid].extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": reply}])
    save_memory()
    await interaction.followup.send(f"🧠 {reply}", view=LazyResponseActions(prompt, uid, messages))

@tree.command(name="image", description="Generate an image")
async def image(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    img = await generate_image(prompt)
    if img:
        await interaction.followup.send(file=discord.File(io.BytesIO(img), filename="lazy_image.png"))
    else:
        await interaction.followup.send("⚠️ Failed to generate image.")

@tree.command(name="say", description="Convert text to speech")
async def say(interaction: discord.Interaction, text: str):
    await interaction.response.defer()
    audio = await text_to_speech(text)
    if audio:
        await interaction.followup.send(file=discord.File(io.BytesIO(audio), filename="lazy_voice.wav"))
    else:
        await interaction.followup.send("⚠️ Failed to speak.")

@tree.command(name="search", description="Search the web")
async def search(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    result = await web_search(query)
    await interaction.followup.send(f"🔍 {result}")

@tree.command(name="set-prefix", description="Set custom prefix")
async def set_prefix(interaction: discord.Interaction, prefix: str):
    prefixes[interaction.guild_id] = prefix
    save_memory()
    await interaction.response.send_message(f"✅ Prefix set to `{prefix}`")

@tree.command(name="set-autoreply-channel", description="Enable replies in this channel")
async def set_channel(interaction: discord.Interaction):
    auto_reply_channels.add(interaction.channel_id)
    save_memory()
    await interaction.response.send_message("✅ Auto replies enabled.")

@tree.command(name="clear-memory", description="Forget chat history")
async def clear(interaction: discord.Interaction):
    user_memory.pop(str(interaction.user.id), None)
    save_memory()
    await interaction.response.send_message("🧠 Memory cleared.")

@tree.command(name="change-personality", description="Change bot's style")
async def change(interaction: discord.Interaction, personality: str):
    personalities[str(interaction.user.id)] = personality
    save_memory()
    await interaction.response.send_message(f"✅ Personality set to: {personality}")

@tree.command(name="help", description="Show command list")
async def help_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("""
**LazyAI Commands**
/ask – Ask anything  
/image – Text to image  
/say – Text to speech  
/search – Web search  
/set-prefix – Custom trigger  
/set-autoreply-channel – Auto-reply here  
/clear-memory – Reset your chat  
/change-personality – Set how I talk to you  
/help – This message  
""")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = str(message.author.id)
    content = message.content.strip()
    cid = message.channel.id
    gid = message.guild.id if message.guild else None

    # Handle audio attachments
    for att in message.attachments:
        if att.content_type and att.content_type.startswith("audio"):
            audio_bytes = await att.read()
            text = await speech_to_text(audio_bytes)
            if text:
                return await handle_prompt(message, text)

    # Channel auto-reply
    if cid in auto_reply_channels:
        return await handle_prompt(message)

    # Prefix-based reply
    prefix = prefixes.get(gid)
    if prefix and content.lower().startswith(prefix.lower()):
        return await handle_prompt(message, content[len(prefix):].strip())

async def handle_prompt(message, prompt_override=None):
    uid = str(message.author.id)
    prompt = prompt_override or message.content
    personality = personalities.get(uid)
    messages = []
    if personality:
        messages.append({"role": "system", "content": f"Adopt this personality: {personality}"})
    messages += user_memory.get(uid, [])[-10:] + [{"role": "user", "content": prompt}]
    reply = await query_hf(messages)

    user_memory.setdefault(uid, []).extend([
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": reply}
    ])
    save_memory()
    await message.channel.send(f"🧠 {reply}", view=LazyResponseActions(prompt, uid, messages))

bot.run(DISCORD_TOKEN)
