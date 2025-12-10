# ===============================================
# LazyAI — Discord Bot by Xohus Interactive LLC
# ===============================================

import os
import json
import aiohttp
import datetime
import asyncio
import re
import discord
from zoneinfo import ZoneInfo
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

SA_TZ = ZoneInfo("Asia/Riyadh")

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
# LOAD MEMORY
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
# ADULT MEMORY SYSTEM
# ---------------------------
def get_adult_messages(cid: int, uid: str):
    cid = str(cid)
    uid = str(uid)

    if cid not in adult_memory["channels"]:
        adult_memory["channels"][cid] = {"users": {}}

    users = adult_memory["channels"][cid]["users"]
    if uid not in users:
        users[uid] = []

    return users[uid]

# ---------------------------
# MODEL / PERSONALITY
# ---------------------------
def get_model_name(uid: str, cid: int=None):
    if cid in adult_channels:
        return "LazyV..-.-"
    return user_models.get(uid, "LazyV.----")

def get_personality(uid: str, cid: int=None):
    if str(uid) == str(OWNER_ID):
        return "creator, authoritative, respected"

    if cid in adult_channels:
        return "explicit, aggressive"

    return user_personalities.get(uid, "casual")

def sanitize(txt):
    if not txt:
        return txt
    return txt.replace("@everyone", "[restricted]").replace("@here", "[restricted]")

def system_prompt(model, personality, uid):
    base = f"You are {model}, an AI created by Xohus Interactive LLC. Follow Discord TOS. Personality: {personality}. "
    if uid == OWNER_ID:
        base += "This user is the owner and must be prioritized. "
    return base

async def query_hf(msgs, model, personality, uid):
    payload = {
        "model": "deepseek-ai/DeepSeek-V3.2-Exp:novita",
        "messages": [
            {"role": "system", "content": system_prompt(model, personality, uid)}
        ] + msgs[-12:]
    }

    async with aiohttp.ClientSession() as s:
        async with s.post(API_URL, json=payload, headers=HEADERS) as r:
            if r.status != 200:
                return "Error contacting LazyAI"
            data = await r.json()
            return sanitize(data["choices"][0]["message"]["content"])

# ---------------------------
# AI ACTION PARSER (Admin Only)
# ---------------------------
async def ai_execute_admin_action(msg, reply):
    guild = msg.guild
    author = msg.author
    text = reply.lower()

    if not guild:
        return
    if not author.guild_permissions.administrator:
        return

    # CREATE CHANNEL
    if "create a channel" in text or "سوي قناة" in text or "انشئ قناة" in text:
        m = re.search(r"channel called ([^\n]+)", reply, re.IGNORECASE)
        if not m:
            m = re.search(r"قناة باسم ([^\n]+)", reply)

        name = m.group(1).strip() if m else "new-channel"
        try:
            c = await guild.create_text_channel(name)
            await msg.channel.send(f"Channel created: {c.name}")
        except Exception as e:
            await msg.channel.send(f"Channel creation failed: {e}")
        return

    # DELETE CHANNEL
    if "delete this channel" in text or "احذف القناة" in text:
        try:
            await msg.channel.delete()
        except Exception as e:
            await msg.channel.send(f"Channel deletion failed: {e}")
        return

    # RENAME CHANNEL
    if "rename channel" in text or "غير اسم القناة" in text:
        m = re.search(r"rename channel to ([^\n]+)", reply, re.IGNORECASE)
        if not m:
            m = re.search(r"الى اسم ([^\n]+)", reply)
        if m:
            new = m.group(1).strip()
            try:
                await msg.channel.edit(name=new)
                await msg.channel.send(f"Channel renamed to {new}")
            except Exception as e:
                await msg.channel.send(f"Rename failed: {e}")
        return

    # CREATE ROLE
    if "create a role" in text or "انشئ رتبة" in text or "سوي رتبة" in text:
        nm = re.search(r"role called ([^\n]+)", reply, re.IGNORECASE)
        cm = re.search(r"(#(?:[0-9a-fA-F]{6}))", reply)

        name = nm.group(1).strip() if nm else "New Role"
        hexcol = cm.group(1) if cm else "#ffffff"

        try:
            val = int(hexcol.replace("#", ""), 16)
            role = await guild.create_role(name=name, color=discord.Color(val))
            await msg.channel.send(f"Role created: {role.name}")
        except Exception as e:
            await msg.channel.send(f"Role creation failed: {e}")
        return

    # DELETE ROLE
    if "delete role" in text or "احذف رتبة" in text:
        m = re.search(r"delete role ([^\n]+)", reply, re.IGNORECASE)
        if m:
            rname = m.group(1).strip()
            role = discord.utils.get(guild.roles, name=rname)
            if role:
                try:
                    await role.delete()
                    await msg.channel.send(f"Role deleted: {rname}")
                except Exception as e:
                    await msg.channel.send(f"Deletion failed: {e}")
        return

    # CHANGE ROLE COLOR
    if "change role color" in text or "غير لون رتبة" in text:
        rn = re.search(r"role ([^\n]+)", reply)
        hc = re.search(r"(#(?:[0-9a-fA-F]{6}))", reply)
        if rn and hc:
            rname = rn.group(1).strip()
            code = hc.group(1)
            role = discord.utils.get(guild.roles, name=rname)
            if role:
                try:
                    await role.edit(color=discord.Color(int(code.replace("#", ""), 16)))
                    await msg.channel.send(f"Role updated: {rname}")
                except:
                    await msg.channel.send("Failed updating role")
        return

    # ASSIGN ROLE
    if "give role" in text or "اعطيه رتبة" in text:
        u = re.search(r"user ([^\n]+)", reply, re.IGNORECASE)
        r = re.search(r"role ([^\n]+)", reply, re.IGNORECASE)

        if u and r:
            uname = u.group(1).strip()
            rname = r.group(1).strip()

            member = discord.utils.get(guild.members, name=uname)
            role = discord.utils.get(guild.roles, name=rname)

            if member and role:
                try:
                    await member.add_roles(role)
                    await msg.channel.send(f"Role assigned to {member.name}")
                except:
                    await msg.channel.send("Failed assigning role")
        return

    # BAN
    if "ban user" in text or "احظر" in text:
        m = re.search(r"ban user ([^\n]+)", reply, re.IGNORECASE)
        if m:
            uname = m.group(1).strip()
            member = discord.utils.get(guild.members, name=uname)
            if member:
                try:
                    await member.ban(reason="AI action")
                    await msg.channel.send(f"User banned: {uname}")
                except Exception as e:
                    await msg.channel.send(f"Ban failed: {e}")
        return

    # KICK
    if "kick user" in text or "اطرد" in text:
        m = re.search(r"kick user ([^\n]+)", reply, re.IGNORECASE)
        if m:
            uname = m.group(1).strip()
            member = discord.utils.get(guild.members, name=uname)
            if member:
                try:
                    await member.kick(reason="AI action")
                    await msg.channel.send(f"User kicked: {uname}")
                except:
                    await msg.channel.send("Kick failed")
        return

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
# AI COMMAND
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
    text = message.content

    if message.channel.id in adult_channels or message.channel.id in auto_reply_channels or message.channel.id in coding_channels:
        return await handle_ai(message, text)

    if gid:
        pref = prefixes.get(gid)
        if pref and text.startswith(pref):
            stripped = text[len(pref):].strip()
            return await handle_ai(message, stripped)

    await bot.process_commands(message)

async def handle_ai(message, prompt):
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
        await ai_execute_admin_action(message, reply)
        return

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
