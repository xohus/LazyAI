# lazyai_merged_full.py

import os
import discord
import aiohttp
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
from dotenv import load_dotenv
import json

# ===============================
# CONFIG
# ===============================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

API_URL = "https://router.huggingface.co/v1/chat/completions"
MEMORY_FILE = "memory.json"

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

# ===============================
# CLIENT
# ===============================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ===============================
# MEMORY
# ===============================
user_memory = {}
user_models = {}
user_personality = {}
prefixes = {}
auto_reply_channels = set()

MODEL_NAMES = {
    "LazyV.----": "deepseek-ai/DeepSeek-V3.2-Exp:novita",
    "LazyV..---": "deepseek-ai/DeepSeek-V3.2-Exp:novita",  # V2
    "LazyV...--": "deepseek-ai/DeepSeek-V3.2-Exp:novita",  # V3
    "LazyV..-.-": "deepseek-ai/DeepSeek-V3.2-Exp:novita"   # Unrestricted
}

MODEL_FEATURES = {
    "LazyV.----": "**LazyV.---- (Original Model / LazyV1)**\n• Personality: Casual, human-like, adaptive\n• Natural, friendly tone\n• Minimal emoji use\n• Occasionally sends spontaneous messages\n• Default by Xohus Interactive LLC",
    "LazyV..---": "**LazyV..--- (LazyV2)**\n• Smarter reasoning\n• Better long replies\n• Emotional awareness\n• Slight humor and tone mimic",
    "LazyV...--": "**LazyV...-- (LazyV3)**\n• Near-human flow\n• Memory linking\n• Deeper conversation personalization\n• Asks about your day",
    "LazyV..-.-": "**LazyV..-.- (Unrestricted)**\n• Few behavior filters\n• Edgy, blunt tone\n• Can say NSFW/sarcastic things\n• Obeys Discord TOS"
}

def load_memory():
    global user_memory, user_models, user_personality, prefixes, auto_reply_channels
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        user_memory = data.get("user_memory", {})
        user_models = data.get("user_models", {})
        user_personality = data.get("user_personality", {})
        prefixes = data.get("prefixes", {})
        auto_reply_channels = set(data.get("auto_reply_channels", []))
        print("[INFO] Memory loaded.")
    except:
        user_memory, user_models, user_personality, prefixes = {}, {}, {}, {}
        auto_reply_channels = set()

def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "user_memory": user_memory,
            "user_models": user_models,
            "user_personality": user_personality,
            "prefixes": prefixes,
            "auto_reply_channels": list(auto_reply_channels)
        }, f, ensure_ascii=False, indent=2)

load_memory()

# ===============================
# QUERY MODEL
# ===============================
async def query_hf(messages, model_key="LazyV.----", personality=""):
    model = MODEL_NAMES.get(model_key, MODEL_NAMES["LazyV.----"])
    sys_prompt = {
        "role": "system",
        "content": f"You are LazyAI, a human-like Discord assistant developed by Xohus Interactive LLC. Default personality: casual, adaptive, no language switching. {personality}"
    }
    payload = {
        "model": model,
        "messages": [sys_prompt] + messages[-10:]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"].replace("DeepSeek", "LazyAI")
            else:
                return "⚠️ LazyAI is currently busy."

# ===============================
# BUTTONS
# ===============================
class LazyAIButtons(View):
    def __init__(self, user_id, prompt):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.prompt = prompt

    @discord.ui.button(label="🔁 Regenerate", style=discord.ButtonStyle.primary)
    async def regenerate(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ Not your message.", ephemeral=True)
        uid = self.user_id
        msgs = user_memory.get(uid, [])
        msgs.append({"role": "user", "content": self.prompt})
        model = user_models.get(uid, "LazyV.----")
        personality = user_personality.get(uid, "")
        reply = await query_hf(msgs, model, personality)
        msgs.append({"role": "assistant", "content": reply})
        user_memory[uid] = msgs
        save_memory()
        await interaction.message.edit(content=f"🧠 {reply}", view=self)

    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ Not your message.", ephemeral=True)
        await interaction.message.delete()

# ===============================
# MODEL DROPDOWN
# ===============================
class ModelDropdown(Select):
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(
            placeholder="Select a model to preview features",
            options=[discord.SelectOption(label=m, description=m) for m in MODEL_NAMES]
        )

    async def callback(self, interaction: discord.Interaction):
        model = self.values[0]
        embed = discord.Embed(title="Model Preview", description=MODEL_FEATURES[model], color=0x00ffcc)
        await interaction.response.edit_message(embed=embed, view=ModelView(self.user_id, model))

class ModelView(View):
    def __init__(self, user_id, current="LazyV.----"):
        super().__init__(timeout=180)
        self.add_item(ModelDropdown(user_id))
        self.add_item(ModelConfirm(user_id, current))

class ModelConfirm(Button):
    def __init__(self, user_id, model_name):
        super().__init__(label="Use This Model", style=discord.ButtonStyle.success)
        self.user_id = user_id
        self.model_name = model_name

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ You can't change another user’s model.", ephemeral=True)
        user_models[self.user_id] = self.model_name
        save_memory()
        await interaction.response.send_message(f"✅ Model set to `{self.model_name}`.", ephemeral=True)

# ===============================
# COMMANDS
# ===============================
@tree.command(name="ask", description="Ask LazyAI anything.")
@app_commands.describe(prompt="Your message")
async def ask(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    uid = str(interaction.user.id)
    model = user_models.get(uid, "LazyV.----")
    personality = user_personality.get(uid, "")
    if uid not in user_memory:
        user_memory[uid] = []
    user_memory[uid].append({"role": "user", "content": prompt})
    reply = await query_hf(user_memory[uid], model, personality)
    user_memory[uid].append({"role": "assistant", "content": reply})
    save_memory()
    await interaction.followup.send(f"🧠 {reply}", view=LazyAIButtons(uid, prompt))

@tree.command(name="set-model", description="Set your preferred LazyAI model")
async def set_model(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    embed = discord.Embed(title="Model Preview", description=MODEL_FEATURES["LazyV.----"], color=0x00ffcc)
    await interaction.response.send_message(
        content="🔧 Select a model below to preview and choose it:",
        embed=embed,
        view=ModelView(uid, "LazyV.----"),
        ephemeral=True
    )

@tree.command(name="set-prefix", description="Set a custom reply prefix")
@app_commands.describe(prefix="Example: 'hey lazy'")
async def set_prefix(interaction: discord.Interaction, prefix: str):
    prefixes[str(interaction.guild_id)] = prefix.lower()
    save_memory()
    await interaction.response.send_message(f"✅ Prefix set to `{prefix}`.")

@tree.command(name="set-autoreply-channel", description="Enable auto-reply in this channel")
async def set_auto(interaction: discord.Interaction):
    auto_reply_channels.add(interaction.channel_id)
    save_memory()
    await interaction.response.send_message("✅ Auto-reply activated.")

@tree.command(name="clear-memory", description="Clear your chat history")
async def clear_memory(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    user_memory.pop(uid, None)
    save_memory()
    await interaction.response.send_message("🧠 Memory cleared.")

# ===============================
# EVENTS
# ===============================
@bot.event
async def on_ready():
    print(f"🧠 LazyAI ready as {bot.user}")
    await tree.sync()

@bot.event
async def on_message(msg):
    if msg.author.bot:
        return
    uid = str(msg.author.id)
    gid = str(msg.guild.id) if msg.guild else None
    if msg.channel.id in auto_reply_channels:
        await handle_message(msg)
    elif gid in prefixes and msg.content.lower().startswith(prefixes[gid]):
        content = msg.content[len(prefixes[gid]):].strip()
        await handle_message(msg, content)

async def handle_message(msg, content_override=None):
    uid = str(msg.author.id)
    content = content_override or msg.content
    model = user_models.get(uid, "LazyV.----")
    personality = user_personality.get(uid, "")
    if uid not in user_memory:
        user_memory[uid] = []
    user_memory[uid].append({"role": "user", "content": content})
    reply = await query_hf(user_memory[uid], model, personality)
    user_memory[uid].append({"role": "assistant", "content": reply})
    save_memory()
    await msg.channel.send(f"🧠 {reply}", view=LazyAIButtons(uid, content))

# ===============================
# RUN
# ===============================
bot.run(DISCORD_TOKEN)
