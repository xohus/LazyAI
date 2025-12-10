# ===============================================
# LazyAI — Discord Bot by Xohus Interactive LLC
# ===============================================

import os
import json
import aiohttp
import datetime
import asyncio
import pytz
import re
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
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
ADULT_MEMORY_FILE = "18mem.json"

OWNER_ID = 1012774928841445426
TARGET_USER_ID = 1382832842446340157

SA_TZ = pytz.timezone("Asia/Riyadh")

# ---------------------------
# DISCORD CLIENT
# ---------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------------------------
# MEMORY STRUCTURES
# ---------------------------
user_memory = {}
adult_memory = {"channels": {}}

prefixes = {}
auto_reply_channels = set()
coding_channels = set()
adult_channels = set()
user_personalities = {}
user_models = {}
linked_accounts = {}
whatsapp_users = {}

# ---------------------------
# MEMORY LOAD/SAVE
# ---------------------------
def load_memory():
    global user_memory, prefixes, auto_reply_channels, coding_channels
    global adult_channels, user_personalities, user_models
    global linked_accounts, whatsapp_users

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

    except:
        user_memory.clear()
        prefixes.clear()
        auto_reply_channels.clear()
        coding_channels.clear()
        adult_channels.clear()
        user_personalities.clear()
        user_models.clear()
        linked_accounts.clear()
        whatsapp_users.clear()

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
    except:
        pass

def load_adult_memory():
    global adult_memory
    try:
        with open(ADULT_MEMORY_FILE, "r", encoding="utf-8") as f:
            adult_memory = json.load(f)
    except:
        adult_memory = {"channels": {}}

def save_adult_memory():
    try:
        with open(ADULT_MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(adult_memory, f, ensure_ascii=False, indent=2)
    except:
        pass

load_memory()
load_adult_memory()

# ---------------------------
# ADULT MEMORY HANDLING
# ---------------------------
def get_adult_messages(channel_id: int, user_id: str):
    cid = str(channel_id)
    uid = str(user_id)

    if cid not in adult_memory["channels"]:
        adult_memory["channels"][cid] = {"users": {}}

    users = adult_memory["channels"][cid]["users"]
    if uid not in users:
        users[uid] = []

    return users[uid]

# ---------------------------
# MODEL/PERSONALITY ENGINE
# ---------------------------
def get_model_name(uid: str, cid: int=None):
    if cid in adult_channels:
        return "LazyV..-.-"
    return user_models.get(uid, "LazyV.----")

def get_personality(uid: str, cid: int=None):
    if str(uid) == str(OWNER_ID):
        return "creator, authoritative, respected"

    if cid in adult_channels:
        return "explicit, unrestricted"

    return user_personalities.get(uid, "casual")

def sanitize(text: str):
    if not text:
        return text
    return text.replace("@everyone", "[restricted]").replace("@here", "[restricted]")

def system_prompt(model, personality, uid):
    base = f"You are {model}, an AI developed by Xohus Interactive LLC. Follow Discord TOS. Personality: {personality}. "
    if uid == OWNER_ID:
        base += "This user is the owner and has highest authority. "
    return base

async def query_hf(messages, model, personality, uid):
    payload = {
        "model": "deepseek-ai/DeepSeek-V3.2-Exp:novita",
        "messages": [
            {"role": "system", "content": system_prompt(model, personality, uid)}
        ] + messages[-12:]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, headers=HEADERS, json=payload) as r:
            if r.status != 200:
                return "Error contacting LazyAI."
            data = await r.json()
            content = data["choices"][0]["message"]["content"]
            return sanitize(content)

# ---------------------------
# NATURAL LANGUAGE ADMIN ACTION SYSTEM
# ---------------------------
async def ai_execute_admin_action(message, reply):
    guild = message.guild
    author = message.author
    text = reply.lower()

    if not guild:
        return None

    if not author.guild_permissions.administrator:
        return None

    # --------------
    # CREATE CHANNEL
    # --------------
    if "create a channel" in text or "انشئ قناة" in text or "سوي قناة" in text:
        m = re.search(r"channel called ([^\n]+)", reply, re.IGNORECASE)
        if not m:
            m = re.search(r"قناة باسم ([^\n]+)", reply)

        name = m.group(1).strip() if m else "new-channel"

        try:
            ch = await guild.create_text_channel(name)
            return await message.channel.send(f"Channel created: {ch.name}")
        except Exception as e:
            return await message.channel.send(f"Channel creation failed: {e}")

    # --------------
    # DELETE CHANNEL
    # --------------
    if "delete this channel" in text or "احذف القناة" in text:
        try:
            await message.channel.delete()
        except Exception as e:
            return await message.channel.send(f"Channel deletion failed: {e}")

    # --------------
    # RENAME CHANNEL
    # --------------
    if "rename channel" in text or "غير اسم القناة" in text:
        m = re.search(r"rename channel to ([^\n]+)", reply, re.IGNORECASE)
        if not m:
            m = re.search(r"الى اسم ([^\n]+)", reply)
        if m:
            new = m.group(1).strip()
            try:
                await message.channel.edit(name=new)
                return await message.channel.send(f"Channel renamed to {new}")
            except Exception as e:
                return await message.channel.send(f"Rename failed: {e}")

    # --------------
    # CREATE ROLE
    # --------------
    if "create a role" in text or "انشئ رتبة" in text or "سوي رتبة" in text:
        name_m = re.search(r"role called ([^\n]+)", reply, re.IGNORECASE)
        color_m = re.search(r"(#(?:[0-9a-fA-F]{6}))", reply)

        name = name_m.group(1).strip() if name_m else "New Role"
        hex_col = color_m.group(1) if color_m else "#ffffff"

        try:
            value = int(hex_col.replace("#", ""), 16)
            role = await guild.create_role(name=name, color=discord.Color(value))
            return await message.channel.send(f"Role created: {role.name}")
        except Exception as e:
            return await message.channel.send(f"Role creation failed: {e}")

    # --------------
    # DELETE ROLE
    # --------------
    if "delete role" in text or "احذف رتبة" in text:
        m = re.search(r"delete role ([^\n]+)", reply, re.IGNORECASE)
        if m:
            rname = m.group(1).strip()
            role = discord.utils.get(guild.roles, name=rname)
            if role:
                try:
                    await role.delete()
                    return await message.channel.send(f"Role deleted: {rname}")
                except Exception as e:
                    return await message.channel.send(f"Deletion failed: {e}")

    # --------------
    # CHANGE ROLE COLOR
    # --------------
    if "change role color" in text or "غير لون رتبة" in text:
        rn = re.search(r"role ([^\n]+)", reply)
        hc = re.search(r"(#(?:[0-9a-fA-F]{6}))", reply)
        if rn and hc:
            rname = rn.group(1).strip()
            hexcode = hc.group(1)
            role = discord.utils.get(guild.roles, name=rname)
            if role:
                try:
                    value = int(hexcode.replace("#", ""), 16)
                    await role.edit(color=discord.Color(value))
                    return await message.channel.send(f"Role updated: {rname}")
                except:
                    return await message.channel.send("Failed updating role")

    # --------------
    # ASSIGN ROLE
    # --------------
    if "give role" in text or "اعطيه رتبة" in text:
        mu = re.search(r"user ([^\n]+)", reply, re.IGNORECASE)
        mr = re.search(r"role ([^\n]+)", reply, re.IGNORECASE)

        if mu and mr:
            uname = mu.group(1).strip()
            rname = mr.group(1).strip()

            member = discord.utils.get(guild.members, name=uname)
            role = discord.utils.get(guild.roles, name=rname)

            if member and role:
                try:
                    await member.add_roles(role)
                    return await message.channel.send(f"Role assigned to {member.name}")
                except:
                    return await message.channel.send("Failed assigning role")

    # --------------
    # BAN USER
    # --------------
    if "ban user" in text or "احظر" in text:
        m = re.search(r"ban user ([^\n]+)", reply, re.IGNORECASE)
        if m:
            uname = m.group(1).strip()
            target = discord.utils.get(guild.members, name=uname)
            if target:
                try:
                    await target.ban(reason="AI instruction")
                    return await message.channel.send(f"User banned: {uname}")
                except Exception as e:
                    return await message.channel.send(f"Ban failed: {e}")

    # --------------
    # KICK USER
    # --------------
    if "kick user" in text or "اطرد" in text:
        m = re.search(r"kick user ([^\n]+)", reply, re.IGNORECASE)
        if m:
            uname = m.group(1).strip()
            target = discord.utils.get(guild.members, name=uname)
            if target:
                try:
                    await target.kick(reason="AI instruction")
                    return await message.channel.send(f"User kicked: {uname}")
                except:
                    return await message.channel.send("Kick failed")

    return None

# ---------------------------
# HOURLY DM SYSTEM
# ---------------------------

async def send_hourly_dms():
    await bot.wait_until_ready()
    target = bot.get_user(TARGET_USER_ID)

    if not target:
        print("Target user not found")
        return

    while True:
        now = datetime.datetime.now(SA_TZ)
        h = now.hour

        if 5 <= h < 12:
            greet = "صباح الخير"
        elif 12 <= h < 17:
            greet = "طاب يومك"
        else:
            greet = "مساء الخير"

        msg = f"{greet} <@{TARGET_USER_ID}>\nجميع البرينروتز موجودين في الحساب Guardian"

        try:
            await target.send(msg)
        except:
            pass

        await asyncio.sleep(3600)

# ---------------------------
# BOT READY
# ---------------------------

@bot.event
async def on_ready():
    print(f"LazyAI logged in as {bot.user}")
    try:
        await tree.sync()
    except:
        pass
    bot.loop.create_task(send_hourly_dms())

# ---------------------------
# AI ASK COMMAND
# ---------------------------

@tree.command(name="ask", description="Ask LazyAI")
async def ask(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()

    uid = str(interaction.user.id)
    cid = interaction.channel_id

    model = get_model_name(uid, cid)
    personality = get_personality(uid, cid)

    if cid in adult_channels:
        msgs = get_adult_messages(cid, uid)
    else:
        msgs = user_memory.setdefault(uid, [])

    msgs.append({"role": "user", "content": prompt})
    reply = await query_hf(msgs, model, personality, uid)
    msgs.append({"role": "assistant", "content": reply})

    if cid in adult_channels:
        save_adult_memory()
    else:
        save_memory()

    await interaction.followup.send(reply)

    fake = type("msg", (object,), {"guild": interaction.guild, "author": interaction.user, "channel": interaction.channel})
    await ai_execute_admin_action(fake, reply)

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

    if message.channel.id in adult_channels or message.channel.id in auto_reply_channels or message.channel.id in coding_channels:
        return await handle_ai_msg(message, content)

    if gid:
        pref = prefixes.get(gid)
        if pref and content.startswith(pref):
            stripped = content[len(pref):].strip()
            return await handle_ai_msg(message, stripped)

    await bot.process_commands(message)

async def handle_ai_msg(message, prompt):
    uid = str(message.author.id)
    cid = message.channel.id

    model = get_model_name(uid, cid)
    personality = get_personality(uid, cid)

    if cid in adult_channels:
        msgs = get_adult_messages(cid, uid)
        msgs.append({"role": "user", "content": prompt})
        reply = await query_hf(msgs, model, personality, uid)
        msgs.append({"role": "assistant", "content": reply})
        save_adult_memory()
        await message.channel.send(reply)
        return await ai_execute_admin_action(message, reply)

    user_memory.setdefault(uid, []).append({"role": "user", "content": prompt})
    reply = await query_hf(user_memory[uid], model, personality, uid)
    user_memory[uid].append({"role": "assistant", "content": reply})
    save_memory()
    await message.channel.send(reply)
    await ai_execute_admin_action(message, reply)

# ---------------------------
# RUN BOT
# ---------------------------

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
