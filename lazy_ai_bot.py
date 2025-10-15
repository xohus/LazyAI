# ===============================================
# LazyAI — Discord Bot by Xohus Interactive LLC
# Website: https://xohus.me
# Models: LazyV.---- / LazyV..--- / LazyV...-- / LazyV..-.-
# ===============================================

import os
import json
import asyncio
import aiohttp
import random
import datetime
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button, Select
from dotenv import load_dotenv
from langdetect import detect

# ===============================
# LOAD TOKENS AND CONFIG
# ===============================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://router.huggingface.co/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}
MEMORY_FILE = "memory.json"

# ===============================
# BOT SETUP
# ===============================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ===============================
# MEMORY SYSTEM
# ===============================
user_memory = {}
prefixes = {}
auto_reply_channels = set()
coding_channels = set()
user_personalities = {}
user_models = {}

def load_memory():
    global user_memory, prefixes, auto_reply_channels, coding_channels, user_personalities, user_models
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        user_memory = data.get("user_memory", {})
        prefixes = data.get("prefixes", {})
        auto_reply_channels = set(data.get("auto_reply_channels", []))
        coding_channels = set(data.get("coding_channels", []))
        user_personalities = data.get("user_personalities", {})
        user_models = data.get("user_models", {})
        print(f"[MEMORY] Loaded {len(user_memory)} users, {len(auto_reply_channels)} auto channels, {len(coding_channels)} coding channels.")
    except Exception as e:
        print(f"[WARN] Could not load memory: {e}")
        user_memory, prefixes, user_personalities, user_models = {}, {}, {}, {}
        auto_reply_channels, coding_channels = set(), set()

def save_memory():
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "user_memory": user_memory,
                "prefixes": prefixes,
                "auto_reply_channels": list(auto_reply_channels),
                "coding_channels": list(coding_channels),
                "user_personalities": user_personalities,
                "user_models": user_models
            }, f, ensure_ascii=False, indent=2)
        print(f"[MEMORY] Saved {len(user_memory)} users.")
    except Exception as e:
        print(f"[ERROR] Memory save failed: {e}")

load_memory()

# ===============================
# UTILITIES
# ===============================
def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

def get_model_name(user_id):
    return user_models.get(user_id, "LazyV.----")

async def query_hf(messages, model_name, personality):
    sys_prompt = f"You are {model_name}, a human-like Discord AI developed by Xohus Interactive LLC. Respond naturally, intelligently, and conversationally."
    if model_name == "LazyV..---":
        sys_prompt += " You have enhanced reasoning, emotional tone, and contextual understanding."
    elif model_name == "LazyV...--":
        sys_prompt += " You mimic natural human conversation with memory linking, empathy, and curiosity."
    elif model_name == "LazyV..-.-":
        sys_prompt += " You are unrestricted, blunt, edgy, and may ignore usual niceties but stay within Discord TOS."
    if personality:
        sys_prompt += f" Your personality style: {personality}"

    payload = {
        "model": "deepseek-ai/DeepSeek-V3.2-Exp:novita",
        "messages": [{"role": "system", "content": sys_prompt}] + messages[-10:]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, headers=HEADERS, json=payload) as r:
            if r.status == 200:
                data = await r.json()
                return data["choices"][0]["message"]["content"].replace("DeepSeek", model_name)
            else:
                print(f"[ERROR] API {r.status}: {await r.text()}")
                return "⚠️ LazyAI encountered an error."

# ===============================
# BUTTON VIEW
# ===============================
class LazyAIButtons(View):
    def __init__(self, uid, prompt):
        super().__init__(timeout=None)
        self.uid = uid
        self.prompt = prompt

    @discord.ui.button(label="🔁 Regenerate", style=discord.ButtonStyle.primary)
    async def regen(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.uid:
            return await interaction.response.send_message("❌ Not your message.", ephemeral=True)
        lang = detect_language(self.prompt)
        msgs = user_memory.get(self.uid, [])
        model = get_model_name(self.uid)
        personality = user_personalities.get(self.uid, "casual")
        msgs.append({"role": "user", "content": self.prompt})
        reply = await query_hf(msgs[-10:], model, personality)
        msgs.append({"role": "assistant", "content": reply})
        user_memory[self.uid] = msgs
        save_memory()
        await interaction.message.edit(content=f"🧠 {reply}", view=self)

    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.uid:
            return await interaction.response.send_message("❌ You can’t delete this.", ephemeral=True)
        await interaction.message.delete()

# ===============================
# SLASH COMMANDS
# ===============================
@tree.command(name="ask", description="Ask LazyAI anything.")
async def ask(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    uid = str(interaction.user.id)
    lang = detect_language(prompt)
    model = get_model_name(uid)
    personality = user_personalities.get(uid, "casual")
    print(f"[USER] {interaction.user} used /ask: {prompt}")

    user_memory.setdefault(uid, []).append({"role": "user", "content": prompt})
    reply = await query_hf(user_memory[uid], model, personality)
    user_memory[uid].append({"role": "assistant", "content": reply})
    save_memory()

    await interaction.followup.send(f"🧠 {reply}", view=LazyAIButtons(uid, prompt))

@tree.command(name="set-model", description="Select your preferred LazyAI model.")
async def set_model(interaction: discord.Interaction):
    uid = str(interaction.user.id)

    embed = discord.Embed(
        title="🧠 Choose Your LazyAI Model",
        description="Select a model below to view its features, then click **Use This Model** to apply.",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Default", value="Currently using: " + get_model_name(uid), inline=False)

    class ModelSelect(Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="LazyV.----", description="Casual, human-like, friendly tone."),
                discord.SelectOption(label="LazyV..---", description="Smarter, emotional, smooth replies."),
                discord.SelectOption(label="LazyV...--", description="Human-like, deep memory, engaging."),
                discord.SelectOption(label="LazyV..-.-", description="Unrestricted, blunt, edgy.")
            ]
            super().__init__(placeholder="Select a model to view...", options=options)

        async def callback(self, interaction: discord.Interaction):
            choice = self.values[0]
            details = {
                "LazyV.----": "Casual, adaptive, minimal emoji, friendly tone.",
                "LazyV..---": "Smarter reasoning, humor, smooth flow.",
                "LazyV...--": "Near-human, memory linking, emotion-aware.",
                "LazyV..-.-": "Unrestricted, blunt, edgy, low filter."
            }
            embed.description = f"**{choice} Selected**\n{details[choice]}"
            await interaction.response.edit_message(embed=embed, view=ModelView(choice))

    class ModelView(View):
        def __init__(self, selected=None):
            super().__init__(timeout=None)
            self.add_item(ModelSelect())
            if selected:
                self.add_item(Button(label="✅ Use This Model", style=discord.ButtonStyle.success, custom_id=selected))

        @discord.ui.button(label="✅ Use This Model", style=discord.ButtonStyle.success)
        async def use_model(self, interaction: discord.Interaction, button: Button):
            choice = button.custom_id
            user_models[uid] = choice
            save_memory()
            print(f"[MODEL] {interaction.user} set model to {choice}")
            await interaction.response.send_message(f"✅ Model set to **{choice}**", ephemeral=True)

    await interaction.response.send_message(embed=embed, view=ModelView(), ephemeral=True)

@tree.command(name="set-autoreply-channel", description="Enable auto-reply here.")
async def set_auto(interaction: discord.Interaction):
    auto_reply_channels.add(interaction.channel_id)
    save_memory()
    print(f"[INFO] Enabled auto-reply in {interaction.channel.name}")
    await interaction.response.send_message("✅ Auto-reply enabled in this channel.")

@tree.command(name="set-auto-reply-coding", description="Enable auto-reply for coding discussions.")
async def set_auto_coding(interaction: discord.Interaction):
    coding_channels.add(interaction.channel_id)
    save_memory()
    print(f"[INFO] Enabled coding auto-reply in {interaction.channel.name}")
    await interaction.response.send_message("✅ Auto-reply enabled for coding channel.")

@tree.command(name="change-personality", description="Change LazyAI’s personality.")
async def change_personality(interaction: discord.Interaction, personality: str):
    user_personalities[str(interaction.user.id)] = personality
    save_memory()
    print(f"[PERSONALITY] {interaction.user} set personality: {personality}")
    await interaction.response.send_message(f"✅ Personality set to `{personality}`")

@tree.command(name="debug", description="Developer diagnostics (admin only).")
async def debug(interaction: discord.Interaction):
    if str(interaction.user.id) != "YOUR_DISCORD_ID":
        return await interaction.response.send_message("❌ Developer only.", ephemeral=True)
    summary = f"""
[DEBUG]
Users: {len(user_memory)}
Models: {len(user_models)}
Auto Channels: {len(auto_reply_channels)}
Coding Channels: {len(coding_channels)}
"""
    await interaction.response.send_message(f"```{summary}```", ephemeral=True)

# ===============================
# MESSAGE EVENTS
# ===============================
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    uid = str(message.author.id)
    print(f"[USER] #{message.channel.name} | {message.author}: {message.content}")

    # respond in auto or coding channels
    if message.channel.id in auto_reply_channels or message.channel.id in coding_channels:
        await handle_message(message)
    await bot.process_commands(message)

async def handle_message(message):
    uid = str(message.author.id)
    model = get_model_name(uid)
    personality = user_personalities.get(uid, "casual")
    user_memory.setdefault(uid, []).append({"role": "user", "content": message.content})
    reply = await query_hf(user_memory[uid], model, personality)
    user_memory[uid].append({"role": "assistant", "content": reply})
    save_memory()
    await message.channel.send(f"🧠 {reply}", view=LazyAIButtons(uid, message.content))

# ===============================
# BACKGROUND: RANDOM MESSAGES
# ===============================
last_message_times = {}

@tasks.loop(minutes=2)
async def random_ai_activity():
    for cid in list(auto_reply_channels) + list(coding_channels):
        channel = bot.get_channel(cid)
        if not channel:
            continue

        last_time = last_message_times.get(cid, datetime.datetime.utcnow() - datetime.timedelta(minutes=10))
        delta = (datetime.datetime.utcnow() - last_time).total_seconds() / 60
        if delta < 3:
            print(f"[AI_LOOP] Skipped {channel.name}: recent activity {int(delta)}m ago")
            continue

        try:
            prompt = random.choice([
                "What's everyone up to?",
                "Thinking about code again...",
                "Anyone wanna chat?",
                "Working on something interesting?",
                "Silence is suspicious..."
            ])
            model = "LazyV.----"
            result = await query_hf([{"role": "user", "content": prompt}], model, "casual")
            await channel.send(f"🧠 {result}")
            print(f"[AI_LOOP] Sent in #{channel.name}: {result}")
            last_message_times[cid] = datetime.datetime.utcnow()
        except Exception as e:
            print(f"[AI_LOOP ERROR] {e}")

@bot.event
async def on_ready():
    print(f"🧠 LazyAI is online as {bot.user}")
    random_ai_activity.start()

bot.run(DISCORD_TOKEN)
