# ===============================================
# LazyAI — Discord Bot by Xohus Interactive LLC
# FULL MERGED VERSION — NATURAL LANGUAGE ADMIN
# HOURLY DM — ALL COMMANDS RESTORED — NO EMOJIS
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
# MEMORY LOAD/SAVE
# ---------------------------
def load_memory():
    global user_memory, prefixes, auto_reply_channels, coding_channels
    global adult_channels, user_personalities, user_models
    global linked_accounts, whatsapp_users

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)

        user_memory = d.get("user_memory", {})
        prefixes = {str(k): v for k, v in d.get("prefixes", {}).items()}
        auto_reply_channels = set(d.get("auto_reply_channels", []))
        coding_channels = set(d.get("coding_channels", []))
        adult_channels = set(d.get("adult_channels", []))
        user_personalities = d.get("user_personalities", {})
        user_models = d.get("user_models", {})
        linked_accounts = d.get("linked_accounts", {})
        whatsapp_users = d.get("whatsapp_users", {})

    except:
        pass

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
# PERSONALITY / MODEL
# ---------------------------
def get_model_name(uid, cid=None):
    if cid in adult_channels:
        return "LazyV..-.-"
    return user_models.get(uid, "LazyV.----")

def get_personality(uid, cid=None):
    if str(uid) == str(OWNER_ID):
        return "creator, authoritative, respected"
    if cid in adult_channels:
        return "explicit, aggressive"
    return user_personalities.get(uid, "casual")

def sanitize(t):
    if not t:
        return t
    return t.replace("@everyone", "[restricted]").replace("@here", "[restricted]")

def system_prompt(model, personality, uid):
    s = f"You are {model}, an AI created by Xohus Interactive LLC. Follow Discord TOS. Personality: {personality}. "
    if uid == OWNER_ID:
        s += "This user is the owner and must be prioritized. "
    return s

async def query_hf(msgs, model, personality, uid):
    payload = {
        "model": "deepseek-ai/DeepSeek-V3.2-Exp:novita",
        "messages": [
            {"role": "system", "content": system_prompt(model, personality, uid)}
        ] + msgs[-12:]
    }

    async with aiohttp.ClientSession() as s:
        async with s.post(API_URL, headers=HEADERS, json=payload) as r:
            if r.status != 200:
                return "Error contacting LazyAI"
            data = await r.json()
            return sanitize(data["choices"][0]["message"]["content"])

# ---------------------------
# NATURAL LANGUAGE ADMIN EXECUTOR
# ---------------------------
async def ai_execute_admin_action(message, reply):
    guild = message.guild
    author = message.author
    t = reply.lower()

    if not guild:
        return
    if not author.guild_permissions.administrator:
        return

    # CREATE CHANNEL
    if "create a channel" in t or "سوي قناة" in t or "انشئ قناة" in t:
        m = re.search(r"channel called ([^\n]+)", reply, re.IGNORECASE)
        if not m:
            m = re.search(r"قناة باسم ([^\n]+)", reply)
        name = m.group(1).strip() if m else "new-channel"
        try:
            ch = await guild.create_text_channel(name)
            await message.channel.send(f"Channel created: {ch.name}")
        except Exception as e:
            await message.channel.send(f"Failed: {e}")
        return

    # DELETE CHANNEL
    if "delete this channel" in t or "احذف القناة" in t:
        try:
            await message.channel.delete()
        except Exception as e:
            await message.channel.send(f"Failed: {e}")
        return

    # RENAME CHANNEL
    if "rename channel" in t or "غير اسم القناة" in t:
        m = re.search(r"rename channel to ([^\n]+)", reply, re.IGNORECASE)
        if not m:
            m = re.search(r"الى اسم ([^\n]+)", reply)
        if m:
            new = m.group(1).strip()
            try:
                await message.channel.edit(name=new)
                await message.channel.send(f"Channel renamed to {new}")
            except Exception as e:
                await message.channel.send(f"Failed: {e}")
        return

    # CREATE ROLE
    if "create a role" in t or "انشئ رتبة" in t or "سوي رتبة" in t:
        nm = re.search(r"role called ([^\n]+)", reply, re.IGNORECASE)
        cm = re.search(r"(#(?:[0-9a-fA-F]{6}))", reply)
        name = nm.group(1).strip() if nm else "New Role"
        hexcol = cm.group(1) if cm else "#ffffff"
        try:
            val = int(hexcol.replace("#", ""), 16)
            r = await guild.create_role(name=name, color=discord.Color(val))
            await message.channel.send(f"Role created: {r.name}")
        except Exception as e:
            await message.channel.send(f"Failed: {e}")
        return

    # DELETE ROLE
    if "delete role" in t or "احذف رتبة" in t:
        m = re.search(r"delete role ([^\n]+)", reply, re.IGNORECASE)
        if m:
            rname = m.group(1).strip()
            role = discord.utils.get(guild.roles, name=rname)
            if role:
                try:
                    await role.delete()
                    await message.channel.send(f"Role deleted: {rname}")
                except Exception as e:
                    await message.channel.send(f"Failed: {e}")
        return

    # CHANGE ROLE COLOR
    if "change role color" in t or "غير لون رتبة" in t:
        rn = re.search(r"role ([^\n]+)", reply)
        hc = re.search(r"(#(?:[0-9a-fA-F]{6}))", reply)
        if rn and hc:
            rname = rn.group(1).strip()
            code = hc.group(1)
            role = discord.utils.get(guild.roles, name=rname)
            if role:
                try:
                    await role.edit(color=discord.Color(int(code.replace("#", ""), 16)))
                    await message.channel.send(f"Role updated: {rname}")
                except:
                    await message.channel.send("Failed to update role")
        return

    # ASSIGN ROLE
    if "give role" in t or "اعطيه رتبة" in t:
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
                    await message.channel.send(f"Role assigned to {member.name}")
                except:
                    await message.channel.send("Failed")
        return

    # BAN USER
    if "ban user" in t or "احظر" in t:
        m = re.search(r"ban user ([^\n]+)", reply, re.IGNORECASE)
        if m:
            uname = m.group(1).strip()
            member = discord.utils.get(guild.members, name=uname)
            if member:
                try:
                    await member.ban(reason="AI instruction")
                    await message.channel.send(f"User banned: {uname}")
                except Exception as e:
                    await message.channel.send(f"Failed: {e}")
        return

    # KICK USER
    if "kick user" in t or "اطرد" in t:
        m = re.search(r"kick user ([^\n]+)", reply, re.IGNORECASE)
        if m:
            uname = m.group(1).strip()
            member = discord.utils.get(guild.members, name=uname)
            if member:
                try:
                    await member.kick(reason="AI instruction")
                    await message.channel.send(f"User kicked: {uname}")
                except:
                    await message.channel.send("Failed")
        return

# ---------------------------
# HOURLY DM SYSTEM
# ---------------------------
async def send_hourly_dms():
    await bot.wait_until_ready()
    u = bot.get_user(TARGET_USER_ID)
    if not u:
        return
    while True:
        now = datetime.datetime.now(SA_TZ)
        h = now.hour
        if 5 <= h < 12:
            g = "صباح الخير"
        elif 12 <= h < 17:
            g = "طاب يومك"
        else:
            g = "مساء الخير"
        msg = f"{g} <@{TARGET_USER_ID}>\n  جميع البرينروتز موجودين في الحساب alwjswq"ا
        try:
            await u.send(msg)
        except:
            pass
        await asyncio.sleep(3600)

# ---------------------------
# ON READY
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
# RESTORED SLASH COMMANDS
# ---------------------------

@tree.command(name="set_prefix", description="Set bot prefix")
async def set_prefix(inter, prefix: str):
    if not inter.guild:
        return await inter.response.send_message("Not in guild", ephemeral=True)
    prefixes[str(inter.guild.id)] = prefix
    save_memory()
    await inter.response.send_message(f"Prefix set to {prefix}")

@tree.command(name="set_model", description="Set your AI model")
async def set_model_cmd(inter, model: str):
    uid = str(inter.user.id)
    user_models[uid] = model
    save_memory()
    await inter.response.send_message(f"Model set to {model}", ephemeral=True)

@tree.command(name="change_personality", description="Change your AI personality")
async def change_personality(inter, personality: str):
    uid = str(inter.user.id)
    user_personalities[uid] = personality
    save_memory()
    await inter.response.send_message(f"Personality set to {personality}", ephemeral=True)

@tree.command(name="set_autoreply_channel", description="Enable AI auto reply here")
async def set_auto(inter):
    auto_reply_channels.add(inter.channel_id)
    save_memory()
    await inter.response.send_message("Auto reply enabled")

@tree.command(name="set_auto_reply_coding", description="Enable coding auto reply here")
async def set_auto_code(inter):
    coding_channels.add(inter.channel_id)
    save_memory()
    await inter.response.send_message("Coding auto reply enabled")

@tree.command(name="auto_reply_18", description="Enable adult mode here")
async def adult(inter):
    adult_channels.add(inter.channel_id)
    save_memory()
    await inter.response.send_message("Channel set to adult mode")

@tree.command(name="link_whatsapp", description="Link WhatsApp number")
async def link_ws(inter, phone: str):
    uid = str(inter.user.id)
    linked_accounts[uid] = f"whatsapp:{phone}"
    whatsapp_users[phone] = {
        "linked_discord": uid,
        "last_interaction": datetime.datetime.utcnow().isoformat(),
        "preferred_language": "en",
        "memory_id": uid
    }
    save_memory()
    await inter.response.send_message("Linked", ephemeral=True)

@tree.command(name="clear_memory", description="Clear your AI memory")
async def clear(inter):
    uid = str(inter.user.id)
    user_memory.pop(uid, None)
    save_memory()
    await inter.response.send_message("Memory cleared")

@tree.command(name="help", description="Show commands")
async def help_cmd(inter):
    txt = """
Commands:
/ask
/set_prefix
/set_model
/set_autoreply_channel
/set_auto_reply_coding
/change_personality
/auto_reply_18
/link_whatsapp
/clear_memory
/help
"""
    await inter.response.send_message(txt, ephemeral=True)

# ---------------------------
# ASK COMMAND
# ---------------------------
@tree.command(name="ask", description="Ask LazyAI")
async def ask(inter, prompt: str):
    await inter.response.defer()
    uid = str(inter.user.id)
    cid = inter.channel_id
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

    await inter.followup.send(reply)

    fake = type("msg", (object,), {"guild": inter.guild, "author": inter.user, "channel": inter.channel})
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
        await ai_execute_admin_action(message, reply)
        return

    user_memory.setdefault(uid, []).append({"role": "user", "content": prompt})
    reply = await query_hf(user_memory[uid], model, personality, uid)
    user_memory[uid].append({"role": "assistant", "content": reply})
    save_memory()
    await message.channel.send(reply)
    await ai_execute_admin_action(message, reply)

# ---------------------------
# LEGACY PREFIX COMMANDS
# ---------------------------

@bot.command(name="lazy")
async def lazy_cmd(ctx, *, prompt: str):
    msg = await handle_ai_msg(ctx.message, prompt)

@bot.command(name="sayto")
async def sayto(ctx, user: discord.User, *, text: str):
    uid = str(ctx.author.id)
    cid = ctx.channel.id
    model = get_model_name(uid, cid)
    personality = get_personality(uid, cid)

    msgs = user_memory.setdefault(uid, [])
    msgs.append({"role": "user", "content": text})
    reply = await query_hf(msgs, model, personality, uid)
    msgs.append({"role": "assistant", "content": reply})
    save_memory()

    await ctx.send(f"<@{user.id}> {reply}")
    fake = type("msg", (object,), {"guild": ctx.guild, "author": ctx.author, "channel": ctx.channel})
    await ai_execute_admin_action(fake, reply)

# ---------------------------
# RUN BOT
# ---------------------------
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
