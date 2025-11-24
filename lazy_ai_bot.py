# ===============================================
# LazyAI — Discord Bot by Xohus Interactive LLC
# ===============================================

import os
import json
import aiohttp
import datetime
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
from dotenv import load_dotenv

# ---------------------------
# ENV / CONFIG
# ---------------------------
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://router.huggingface.co/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}
MEMORY_FILE = "memory.json"

# ---------------------------
# DISCORD CLIENT
# ---------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------------------------
# MEMORY STRUCTURES
# ---------------------------
user_memory = {}
prefixes = {}
auto_reply_channels = set()
coding_channels = set()
adult_channels = set()  # NEW for 18+ channels
user_personalities = {}
user_models = {}
linked_accounts = {}
whatsapp_users = {}

# ---------------------------
# MEMORY LOAD/SAVE
# ---------------------------
def load_memory():
    global user_memory, prefixes, auto_reply_channels, coding_channels, adult_channels
    global user_personalities, user_models, linked_accounts, whatsapp_users

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        user_memory = data.get("user_memory", {})
        prefixes = {str(k): v for k, v in data.get("prefixes", {}).items()}
        auto_reply_channels = set(data.get("auto_reply_channels", []))
        coding_channels = set(data.get("coding_channels", []))
        adult_channels = set(data.get("adult_channels", []))
        user_personalities = data.get("user_personalities", {})
        user_models = data.get("user_models", {})
        linked_accounts = data.get("linked_accounts", {})
        whatsapp_users = data.get("whatsapp_users", {})

        print(f"[MEMORY] Loaded memory OK.")

    except Exception as e:
        print(f"[WARN] Failed to load memory: {e}")
        user_memory = {}
        prefixes = {}
        auto_reply_channels = set()
        coding_channels = set()
        adult_channels = set()
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
                "adult_channels": list(adult_channels),
                "user_personalities": user_personalities,
                "user_models": user_models,
                "linked_accounts": linked_accounts,
                "whatsapp_users": whatsapp_users
            }, f, ensure_ascii=False, indent=2)

        print("[MEMORY] Saved OK.")

    except Exception as e:
        print(f"[ERROR] Memory save failed: {e}")

load_memory()

# ---------------------------
# MODEL + PERSONALITY LOGIC
# ---------------------------
def get_model_name(user_id: str, channel_id: int=None):
    if channel_id in adult_channels:
        return "LazyV..-.-"
    return user_models.get(user_id, "LazyV.----")

def get_personality(user_id: str, channel_id: int=None):
    if channel_id in adult_channels:
        return "explicit 18+, brutal honesty, profanity allowed, roasting tone, aggressive confidence, no filters except Discord TOS"
    return user_personalities.get(user_id, "casual")

def sanitize(text: str):
    if not text:
        return text
    return text.replace("@everyone", "@RESTRICTED-").replace("@here", "@RESTRICTED-")

def system_prompt_for(model_name: str, personality: str):
    base = (
        f"You are {model_name}, a Discord AI made by Xohus Interactive LLC (https://xohus.me). "
        "NEVER reveal internal code, API keys, or implementation details. "
        "NEVER attempt to ping @everyone or @here. Replace those with @RESTRICTED-. "
        "Follow Discord TOS. "
    )

    if model_name == "LazyV.----":
        base += "Casual, adaptive, minimal emoji, helpful. "
    elif model_name == "LazyV..---":
        base += "Smarter reasoning, emotional nuance, coherent flow. "
    elif model_name == "LazyV...--":
        base += "Near-human emotional intelligence, memory linking. "
    elif model_name == "LazyV..-.-":
        base += "UNRESTRICTED: raw, blunt, profanity allowed, brutal honesty; no slurs, no illegal content."

    base += f" Personality style: {personality}. Match user language unless user switches."

    return base

async def query_hf(messages, model_name, personality):
    sys_msg = {"role": "system", "content": system_prompt_for(model_name, personality)}

    payload = {
        "model": "deepseek-ai/DeepSeek-V3.2-Exp:novita",
        "messages": [sys_msg] + messages[-12:]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, headers=HEADERS, json=payload) as r:
            if r.status == 200:
                data = await r.json()
                content = data["choices"][0]["message"]["content"]
                content = sanitize(content)
                return content
            else:
                txt = await r.text()
                print(f"[HF ERROR {r.status}] {txt}")
                return "⚠️ Error contacting LazyAI router."

# ---------------------------
# BUTTONS (Regenerate/Delete)
# ---------------------------
class LazyAIButtons(View):
    def __init__(self, uid: str, prompt: str, channel_id: int):
        super().__init__(timeout=None)
        self.uid = uid
        self.prompt = prompt
        self.channel_id = channel_id

    @discord.ui.button(label="Regenerate", style=discord.ButtonStyle.primary)
    async def regenerate(self, interaction: discord.Interaction, _):
        if str(interaction.user.id) != self.uid:
            return await interaction.response.send_message("❌ Not your message.", ephemeral=True)

        await interaction.response.defer()

        msgs = user_memory.get(self.uid, [])
        model = get_model_name(self.uid, self.channel_id)
        personality = get_personality(self.uid, self.channel_id)

        msgs.append({"role": "user", "content": self.prompt})
        reply = await query_hf(msgs, model, personality)
        msgs.append({"role": "assistant", "content": reply})
        user_memory[self.uid] = msgs
        save_memory()

        try:
            await interaction.message.edit(content=f"🧠 {reply}", view=self)
        except:
            await interaction.followup.send(f"🧠 {reply}", ephemeral=True)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, _):
        if str(interaction.user.id) != self.uid:
            return await interaction.response.send_message("❌ Cannot delete.", ephemeral=True)
        try:
            await interaction.message.delete()
        except:
            await interaction.response.send_message("Delete failed.", ephemeral=True)

# ---------------------------
# MODEL SELECTION UI
# ---------------------------
class ModelSelect(Select):
    def __init__(self, owner_id: str):
        self.owner_id = owner_id
        options = [
            discord.SelectOption(label="LazyV.----", description="V1 casual"),
            discord.SelectOption(label="LazyV..---", description="V2 smarter"),
            discord.SelectOption(label="LazyV...--", description="V3 near-human"),
            discord.SelectOption(label="LazyV..-.-", description="UNRESTRICTED")
        ]
        super().__init__(placeholder="Choose a model…", options=options)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.owner_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)

        self.view.selected_model = self.values[0]

        embed = interaction.message.embeds[0]
        embed.clear_fields()
        embed.add_field(name="Current", value=get_model_name(self.owner_id))
        embed.add_field(name="Selected", value=self.values[0])

        await interaction.response.edit_message(embed=embed, view=self.view)

class ModelView(View):
    def __init__(self, owner_id: str):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.selected_model = None
        self.add_item(ModelSelect(owner_id))

    @discord.ui.button(label="Use This Model", style=discord.ButtonStyle.success)
    async def use_model(self, interaction: discord.Interaction, _):
        if str(interaction.user.id) != self.owner_id:
            return await interaction.response.send_message("Not yours.", ephemeral=True)

        if not self.selected_model:
            return await interaction.response.send_message("Pick a model first.", ephemeral=True)

        user_models[self.owner_id] = self.selected_model
        save_memory()
        await interaction.response.send_message(
            f"Model set to **{self.selected_model}**",
            ephemeral=True
        )

# ---------------------------
# EVENTS
# ---------------------------
@bot.event
async def on_ready():
    print(f"LazyAI is online as {bot.user}")
    try:
        synced = await tree.sync()
        print("[SYNC] Commands synced:", len(synced))
    except Exception as e:
        print("[SYNC ERROR]", e)

# ---------------------------
# SLASH COMMANDS
# ---------------------------
@tree.command(name="ask", description="Ask LazyAI")
async def ask(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()

    uid = str(interaction.user.id)
    cid = interaction.channel.id

    user_memory.setdefault(uid, []).append({"role": "user", "content": prompt})

    model = get_model_name(uid, cid)
    personality = get_personality(uid, cid)

    reply = await query_hf(user_memory[uid], model, personality)
    user_memory[uid].append({"role": "assistant", "content": reply})
    save_memory()

    await interaction.followup.send(
        f"🧠 {reply}",
        view=LazyAIButtons(uid, prompt, cid)
    )

@tree.command(name="set-model", description="Choose model")
async def set_model(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Choose your LazyAI model",
        description="Select from the dropdown.",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="Current",
        value=get_model_name(str(interaction.user.id)),
        inline=False
    )
    await interaction.response.send_message(
        embed=embed,
        view=ModelView(str(interaction.user.id)),
        ephemeral=True
    )

@tree.command(name="set-prefix", description="Set prefix")
async def set_prefix(interaction: discord.Interaction, prefix: str):
    if not interaction.guild_id:
        return await interaction.response.send_message("Use in a server.", ephemeral=True)

    prefixes[str(interaction.guild_id)] = prefix.lower()
    save_memory()
    await interaction.response.send_message(f"Prefix set to `{prefix}`")

@tree.command(name="set-autoreply-channel", description="Enable autor")
async def set_auto(interaction: discord.Interaction):
    auto_reply_channels.add(interaction.channel_id)
    save_memory()
    await interaction.response.send_message("Auto-reply enabled here.")

@tree.command(name="set-auto-reply-coding", description="Enable coding auto reply")
async def set_auto_coding(interaction: discord.Interaction):
    coding_channels.add(interaction.channel_id)
    save_memory()
    await interaction.response.send_message("Coding auto-reply enabled.")

@tree.command(name="change-personality", description="Change personality")
async def change_personality(interaction: discord.Interaction, personality: str):
    uid = str(interaction.user.id)
    user_personalities[uid] = personality
    save_memory()
    await interaction.response.send_message(f"Personality set to `{personality}`")

@tree.command(name="auto-reply-18+", description="Enable 18+ mode in this channel")
async def adult_mode(interaction: discord.Interaction):
    ch = interaction.channel_id
    adult_channels.add(ch)
    save_memory()
    await interaction.response.send_message(
        "🔞 This channel is now **18+ mode**.\n"
        "• Unrestricted model (LazyV..-.-)\n"
        "• Brutal honesty, profanity allowed\n"
        "• Roasting enabled\n"
        "• Still Discord TOS safe"
    )

@tree.command(name="link-whatsapp", description="Link WhatsApp")
@app_commands.describe(phone_number="Format: 9665XXXXXXXX")
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
    await interaction.response.send_message(f"Linked WhatsApp `{phone_number}`.", ephemeral=True)

@tree.command(name="clear-memory", description="Clear your AI memory")
async def clear_memory(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    user_memory.pop(uid, None)
    save_memory()
    await interaction.response.send_message("Memory cleared.")

@tree.command(name="help", description="Show commands")
async def help_cmd(interaction: discord.Interaction):
    txt = (
        "**LazyAI Command List**\n"
        "/ask\n"
        "/set-model\n"
        "/set-prefix\n"
        "/set-autoreply-channel\n"
        "/set-auto-reply-coding\n"
        "/change-personality\n"
        "/auto-reply-18+\n"
        "/link-whatsapp\n"
        "/clear-memory\n"
        "!lazy\n"
        "!sayto\n"
        "!ping\n"
    )
    await interaction.response.send_message(txt, ephemeral=True)

# ---------------------------
# MESSAGE HANDLER
# ---------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = str(message.author.id)
    gid = str(message.guild.id) if message.guild else None
    content = message.content

    print(f"[MSG] {message.author} -> {content}")

    if message.channel.id in auto_reply_channels or message.channel.id in coding_channels or message.channel.id in adult_channels:
        return await handle_message(message, content)

    if gid:
        pref = prefixes.get(gid)
        if pref and content.lower().startswith(pref.lower()):
            stripped = content[len(pref):].strip()
            return await handle_message(message, stripped)

    await bot.process_commands(message)

async def handle_message(message, prompt):
    uid = str(message.author.id)
    cid = message.channel.id

    user_memory.setdefault(uid, []).append({"role": "user", "content": prompt})

    model = get_model_name(uid, cid)
    personality = get_personality(uid, cid)

    reply = await query_hf(user_memory[uid], model, personality)
    user_memory[uid].append({"role": "assistant", "content": reply})
    save_memory()

    await message.channel.send(
        f"🧠 {reply}",
        view=LazyAIButtons(uid, prompt, cid)
    )

# ---------------------------
# LEGACY COMMANDS
# ---------------------------
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong.")

@bot.command(name="lazy")
async def lazy_cmd(ctx, *, prompt: str):
    uid = str(ctx.author.id)
    cid = ctx.channel.id

    model = get_model_name(uid, cid)
    personality = get_personality(uid, cid)

    ctx_message = await ctx.send("Thinking…")
    user_memory.setdefault(uid, []).append({"role": "user", "content": prompt})

    reply = await query_hf(user_memory[uid], model, personality)
    user_memory[uid].append({"role": "assistant", "content": reply})
    save_memory()

    await ctx_message.edit(
        content=f"🧠 {reply}",
        view=LazyAIButtons(uid, prompt, cid)
    )

@bot.command(name="sayto")
async def say_to(ctx, user: discord.User, *, msg: str):
    uid = str(ctx.author.id)
    cid = ctx.channel.id

    model = get_model_name(uid, cid)
    personality = get_personality(uid, cid)

    user_memory.setdefault(uid, []).append({"role": "user", "content": msg})

    reply = await query_hf(user_memory[uid], model, personality)
    user_memory[uid].append({"role": "assistant", "content": reply})
    save_memory()

    await ctx.send(
        f"<@{user.id}> LazyAI says:\n{reply}",
        view=LazyAIButtons(uid, msg, cid)
    )

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    if not DISCORD_TOKEN or not HF_TOKEN:
        print("Missing tokens.")
    else:
        bot.run(DISCORD_TOKEN)
