import discord
from discord import app_commands
from discord.ext import commands
import os
import aiohttp
from dotenv import load_dotenv
from langdetect import detect
import json
import io
import shutil

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# Endpoints
CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_NAME = "deepseek-ai/DeepSeek-V3.2-Exp:novita"
IMAGE_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"
TTS_URL = "https://api-inference.huggingface.co/models/suno/bark"
SPEECH_TO_TEXT_URL = "https://api-inference.huggingface.co/models/openai/whisper-1"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

MEMORY_FILE = "memory.json"

user_memory = {}
prefixes = {}
auto_reply_channels = set()

def load_memory():
    global user_memory, prefixes, auto_reply_channels
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            user_memory = data.get("user_memory", {})
            prefixes = data.get("prefixes", {})
            auto_reply_channels = set(data.get("auto_reply_channels", []))
        except Exception as e:
            print("⚠️ Failed to load memory:", e)

def save_memory():
    data = {
        "user_memory": user_memory,
        "prefixes": prefixes,
        "auto_reply_channels": list(auto_reply_channels)
    }
    tmp = MEMORY_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        shutil.move(tmp, MEMORY_FILE)
    except Exception as e:
        print("⚠️ Failed to save memory:", e)

# Load persisted memory at startup
load_memory()

def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

async def query_hf(messages):
    payload = {
        "messages": messages,
        "model": MODEL_NAME
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(CHAT_URL, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                content = data["choices"][0]["message"]["content"]
                return content.replace("DeepSeek", "LazyAI")
            else:
                err = await resp.text()
                print(f"[ERROR] Chat API {resp.status}: {err}")
                return "⚠️ LazyAI is sleepy. Try again later."

async def generate_image(prompt):
    async with aiohttp.ClientSession() as session:
        async with session.post(IMAGE_URL, headers=HEADERS, json={"inputs": prompt}) as resp:
            if resp.status == 200:
                return await resp.read()
            return None

async def text_to_speech(prompt):
    async with aiohttp.ClientSession() as session:
        async with session.post(TTS_URL, headers=HEADERS, json={"inputs": prompt}) as resp:
            if resp.status == 200:
                return await resp.read()
            return None

async def speech_to_text(audio_bytes):
    async with aiohttp.ClientSession() as session:
        payload = {"inputs": base64.b64encode(audio_bytes).decode()}
        async with session.post(SPEECH_TO_TEXT_URL, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("text", "")
            return ""

async def web_search(query: str):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.duckduckgo.com/", params={"q": query, "format": "json", "no_redirect": 1}) as resp:
            data = await resp.json()
            return data.get("AbstractText") or "🔍 No result found."

@bot.event
async def on_ready():
    print(f"🧠 LazyAI is online as {bot.user}.")
    try:
        synced = await tree.sync()
        print(f"[INFO] Synced {len(synced)} slash commands.")
    except Exception as e:
        print("Command sync failed:", e)

@tree.command(name="ask", description="Ask LazyAI anything.")
@app_commands.describe(prompt="Your message or question")
async def slash_ask(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    uid = str(interaction.user.id)
    if uid not in user_memory:
        user_memory[uid] = []
    user_memory[uid].append({"role": "user", "content": prompt})

    response = await query_hf(user_memory[uid])
    user_memory[uid].append({"role": "assistant", "content": response})
    save_memory()

    await interaction.followup.send(f"🧠 {response}")

@tree.command(name="image", description="Generate an image from text")
@app_commands.describe(prompt="Describe what image you want")
async def slash_image(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    img = await generate_image(prompt)
    if img:
        await interaction.followup.send(file=discord.File(io.BytesIO(img), filename="lazy_image.png"))
    else:
        await interaction.followup.send("⚠️ Couldn't generate image.")

@tree.command(name="say", description="Convert text to voice")
@app_commands.describe(text="What LazyAI should say aloud")
async def slash_say(interaction: discord.Interaction, text: str):
    await interaction.response.defer()
    audio = await text_to_speech(text)
    if audio:
        await interaction.followup.send(file=discord.File(io.BytesIO(audio), filename="lazy_speech.wav"))
    else:
        await interaction.followup.send("⚠️ Voice generation failed.")

@tree.command(name="search", description="Search the web")
@app_commands.describe(query="Your search term")
async def slash_search(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    result = await web_search(query)
    await interaction.followup.send(f"🔍 {result}")

@tree.command(name="set-prefix", description="Set custom prefix")
@app_commands.describe(prefix="Word or phrase")
async def slash_set_prefix(interaction: discord.Interaction, prefix: str):
    prefixes[interaction.guild_id] = prefix.lower()
    save_memory()
    await interaction.response.send_message(f"✅ Prefix set to `{prefix}`")

@tree.command(name="set-autoreply-channel", description="Enable auto replies in this channel")
async def slash_auto(interaction: discord.Interaction):
    auto_reply_channels.add(interaction.channel_id)
    save_memory()
    await interaction.response.send_message("✅ Auto‑reply enabled here.")

@tree.command(name="clear-memory", description="Clear conversation memory for you")
async def slash_clear(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    user_memory.pop(uid, None)
    save_memory()
    await interaction.response.send_message("🧠 Memory cleared!")

@tree.command(name="help", description="Show LazyAI commands")
async def slash_help(interaction: discord.Interaction):
    await interaction.response.send_message("""
**LazyAI Commands**

`/ask` — Chat with LazyAI  
`/image` — Generate image  
`/say` — Text to speech  
`/search` — Web search  
`/set-prefix` — Set prefix  
`/set-autoreply-channel` — Auto replies here  
`/clear-memory` — Reset memory  
`/help` — Show this help message
""")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = str(message.author.id)
    content = message.content.strip()
    gid = message.guild.id if message.guild else None
    cid = message.channel.id

    # If has audio attachment
    if message.attachments:
        for att in message.attachments:
            if att.content_type and att.content_type.startswith("audio"):
                audio_bytes = await att.read()
                text = await speech_to_text(audio_bytes)
                if text:
                    await handle_message(message, prompt_override=text)
                    return

    if cid in auto_reply_channels:
        await handle_message(message)
        return

    prefix = prefixes.get(gid)
    if prefix and content.lower().startswith(prefix.lower()):
        stripped = content[len(prefix):].strip()
        await handle_message(message, prompt_override=stripped)

async def handle_message(message, prompt_override=None):
    prompt = prompt_override if prompt_override else message.content
    uid = str(message.author.id)

    if uid not in user_memory:
        user_memory[uid] = []
    user_memory[uid].append({"role": "user", "content": prompt})

    response = await query_hf(user_memory[uid])
    user_memory[uid].append({"role": "assistant", "content": response})
    save_memory()

    await message.channel.send(f" {response}")

bot.run(DISCORD_TOKEN)
