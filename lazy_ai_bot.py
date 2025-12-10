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
import logging
from typing import Dict, List, Set, Optional
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv

# —————————

# LOGGING CONFIGURATION

# —————————

logging.basicConfig(
level=logging.INFO,
format=’%(asctime)s - %(name)s - %(levelname)s - %(message)s’
)
logger = logging.getLogger(**name**)

# —————————

# ENV / CONFIG

# —————————

load_dotenv()
DISCORD_TOKEN = os.getenv(“DISCORD_TOKEN”)
HF_TOKEN = os.getenv(“HF_TOKEN”)

if not DISCORD_TOKEN or not HF_TOKEN:
raise ValueError(“Missing required environment variables: DISCORD_TOKEN and/or HF_TOKEN”)

API_URL = “https://router.huggingface.co/v1/chat/completions”
HEADERS = {“Authorization”: f”Bearer {HF_TOKEN}”}

MEMORY_FILE = “memory.json”
ADULT_MEMORY_FILE = “18mem.json”

OWNER_ID = 1012774928841445426
TARGET_USER_ID = 1382832842446340157

SA_TZ = ZoneInfo(“Asia/Riyadh”)

# —————————

# DISCORD CLIENT

# —————————

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=”!”, intents=intents, help_command=None)
tree = bot.tree

# —————————

# MEMORY STRUCTURES WITH TYPE HINTS

# —————————

user_memory: Dict[str, List[Dict[str, str]]] = {}
adult_memory: Dict[str, Dict] = {“channels”: {}}

prefixes: Dict[str, str] = {}
auto_reply_channels: Set[int] = set()
coding_channels: Set[int] = set()
adult_channels: Set[int] = set()
user_personalities: Dict[str, str] = {}
user_models: Dict[str, str] = {}
linked_accounts: Dict[str, str] = {}
whatsapp_users: Dict[str, Dict] = {}

# —————————

# MEMORY LOAD/SAVE WITH ERROR HANDLING

# —————————

def load_memory() -> None:
“”“Load bot memory from JSON file with error handling.”””
global user_memory, prefixes, auto_reply_channels, coding_channels
global adult_channels, user_personalities, user_models
global linked_accounts, whatsapp_users

```
try:
    if not os.path.exists(MEMORY_FILE):
        logger.info(f"{MEMORY_FILE} not found, starting with empty memory")
        return

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
    
    logger.info(f"Successfully loaded memory from {MEMORY_FILE}")
except json.JSONDecodeError as e:
    logger.error(f"JSON decode error in {MEMORY_FILE}: {e}")
except Exception as e:
    logger.error(f"Error loading memory: {e}")
```

def save_memory() -> None:
“”“Save bot memory to JSON file with error handling.”””
try:
data = {
“user_memory”: user_memory,
“prefixes”: prefixes,
“auto_reply_channels”: list(auto_reply_channels),
“coding_channels”: list(coding_channels),
“adult_channels”: list(adult_channels),
“user_personalities”: user_personalities,
“user_models”: user_models,
“linked_accounts”: linked_accounts,
“whatsapp_users”: whatsapp_users
}

```
    # Write to temp file first, then rename (atomic operation)
    temp_file = f"{MEMORY_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    os.replace(temp_file, MEMORY_FILE)
    logger.debug("Memory saved successfully")
except Exception as e:
    logger.error(f"Error saving memory: {e}")
```

def load_adult_memory() -> None:
“”“Load adult memory from JSON file.”””
global adult_memory
try:
if not os.path.exists(ADULT_MEMORY_FILE):
logger.info(f”{ADULT_MEMORY_FILE} not found, starting with empty adult memory”)
return

```
    with open(ADULT_MEMORY_FILE, "r", encoding="utf-8") as f:
        adult_memory = json.load(f)
    logger.info(f"Successfully loaded adult memory from {ADULT_MEMORY_FILE}")
except Exception as e:
    logger.error(f"Error loading adult memory: {e}")
    adult_memory = {"channels": {}}
```

def save_adult_memory() -> None:
“”“Save adult memory to JSON file.”””
try:
temp_file = f”{ADULT_MEMORY_FILE}.tmp”
with open(temp_file, “w”, encoding=“utf-8”) as f:
json.dump(adult_memory, f, ensure_ascii=False, indent=2)
os.replace(temp_file, ADULT_MEMORY_FILE)
logger.debug(“Adult memory saved successfully”)
except Exception as e:
logger.error(f”Error saving adult memory: {e}”)

# Initialize memory on startup

load_memory()
load_adult_memory()

# —————————

# PERSONALITY / MODEL FUNCTIONS

# —————————

def get_model_name(uid: str, cid: Optional[int] = None) -> str:
“”“Get the model name for a user/channel.”””
if cid in adult_channels:
return “LazyV..-.-”
return user_models.get(uid, “LazyV.––”)

def get_personality(uid: str, cid: Optional[int] = None) -> str:
“”“Get the personality for a user/channel.”””
if str(uid) == str(OWNER_ID):
return “creator, authoritative, respected”
if cid in adult_channels:
return “explicit, aggressive”
return user_personalities.get(uid, “casual”)

def sanitize(text: str) -> str:
“”“Sanitize text to prevent mentions abuse.”””
if not text:
return text
return text.replace(”@everyone”, “[restricted]”).replace(”@here”, “[restricted]”)

def system_prompt(model: str, personality: str, uid: str) -> str:
“”“Generate system prompt for AI.”””
prompt = f”You are {model}, an AI created by Xohus Interactive LLC. Follow Discord TOS. Personality: {personality}. “
if str(uid) == str(OWNER_ID):
prompt += “This user is the owner and must be prioritized. “
return prompt

def get_adult_messages(channel_id: int, user_id: str) -> List[Dict[str, str]]:
“”“Get adult channel messages.”””
channel_key = str(channel_id)
if channel_key not in adult_memory[“channels”]:
adult_memory[“channels”][channel_key] = {}
if user_id not in adult_memory[“channels”][channel_key]:
adult_memory[“channels”][channel_key][user_id] = []
return adult_memory[“channels”][channel_key][user_id]

# —————————

# API QUERY WITH RETRY LOGIC

# —————————

async def query_hf(msgs: List[Dict[str, str]], model: str, personality: str, uid: str, retries: int = 3) -> str:
“”“Query Hugging Face API with retry logic.”””
payload = {
“model”: “deepseek-ai/DeepSeek-V3.2-Exp:novita”,
“messages”: [
{“role”: “system”, “content”: system_prompt(model, personality, uid)}
] + msgs[-12:],
“max_tokens”: 2000,
“temperature”: 0.7
}

```
for attempt in range(retries):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=HEADERS, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"API error {response.status}: {error_text}")
                    if attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return f"Error: API returned status {response.status}"
                
                data = await response.json()
                content = data["choices"][0]["message"]["content"]
                return sanitize(content)
    except asyncio.TimeoutError:
        logger.error(f"Timeout on attempt {attempt + 1}")
        if attempt < retries - 1:
            await asyncio.sleep(2 ** attempt)
            continue
        return "Error: Request timed out"
    except Exception as e:
        logger.error(f"Query error on attempt {attempt + 1}: {e}")
        if attempt < retries - 1:
            await asyncio.sleep(2 ** attempt)
            continue
        return f"Error: {str(e)}"

return "Error: Failed after multiple retries"
```

# —————————

# NATURAL LANGUAGE ADMIN EXECUTOR

# —————————

async def ai_execute_admin_action(message: discord.Message, reply: str) -> None:
“”“Execute admin actions based on AI response.”””
guild = message.guild
author = message.author

```
if not guild:
    return
if not author.guild_permissions.administrator:
    return

reply_lower = reply.lower()

try:
    # CREATE CHANNEL
    if "create a channel" in reply_lower or "سوي قناة" in reply_lower or "انشئ قناة" in reply_lower:
        match = re.search(r"channel called ([^\n]+)", reply, re.IGNORECASE)
        if not match:
            match = re.search(r"قناة باسم ([^\n]+)", reply)
        name = match.group(1).strip() if match else "new-channel"
        
        channel = await guild.create_text_channel(name)
        await message.channel.send(f"Channel created: {channel.mention}")
        logger.info(f"Created channel {name} in guild {guild.id}")
        return

    # DELETE CHANNEL
    if "delete this channel" in reply_lower or "احذف القناة" in reply_lower:
        channel_name = message.channel.name
        await message.channel.delete()
        logger.info(f"Deleted channel {channel_name} in guild {guild.id}")
        return

    # RENAME CHANNEL
    if "rename channel" in reply_lower or "غير اسم القناة" in reply_lower:
        match = re.search(r"rename channel to ([^\n]+)", reply, re.IGNORECASE)
        if not match:
            match = re.search(r"الى اسم ([^\n]+)", reply)
        if match:
            new_name = match.group(1).strip()
            old_name = message.channel.name
            await message.channel.edit(name=new_name)
            await message.channel.send(f"Channel renamed from {old_name} to {new_name}")
            logger.info(f"Renamed channel from {old_name} to {new_name}")
        return

    # CREATE ROLE
    if "create a role" in reply_lower or "انشئ رتبة" in reply_lower or "سوي رتبة" in reply_lower:
        name_match = re.search(r"role called ([^\n]+)", reply, re.IGNORECASE)
        color_match = re.search(r"(#(?:[0-9a-fA-F]{6}))", reply)
        
        role_name = name_match.group(1).strip() if name_match else "New Role"
        hex_color = color_match.group(1) if color_match else "#ffffff"
        
        color_value = int(hex_color.replace("#", ""), 16)
        role = await guild.create_role(name=role_name, color=discord.Color(color_value))
        await message.channel.send(f"Role created: {role.mention}")
        logger.info(f"Created role {role_name} in guild {guild.id}")
        return

    # DELETE ROLE
    if "delete role" in reply_lower or "احذف رتبة" in reply_lower:
        match = re.search(r"delete role ([^\n]+)", reply, re.IGNORECASE)
        if match:
            role_name = match.group(1).strip()
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                await role.delete()
                await message.channel.send(f"Role deleted: {role_name}")
                logger.info(f"Deleted role {role_name}")
        return

    # CHANGE ROLE COLOR
    if "change role color" in reply_lower or "غير لون رتبة" in reply_lower:
        role_match = re.search(r"role ([^\n]+)", reply)
        color_match = re.search(r"(#(?:[0-9a-fA-F]{6}))", reply)
        
        if role_match and color_match:
            role_name = role_match.group(1).strip()
            hex_code = color_match.group(1)
            role = discord.utils.get(guild.roles, name=role_name)
            
            if role:
                color_value = int(hex_code.replace("#", ""), 16)
                await role.edit(color=discord.Color(color_value))
                await message.channel.send(f"Role color updated: {role_name} to {hex_code}")
                logger.info(f"Updated role color for {role_name}")
        return

    # ASSIGN ROLE
    if "give role" in reply_lower or "اعطيه رتبة" in reply_lower:
        user_match = re.search(r"user ([^\n]+)", reply, re.IGNORECASE)
        role_match = re.search(r"role ([^\n]+)", reply, re.IGNORECASE)
        
        if user_match and role_match:
            user_name = user_match.group(1).strip()
            role_name = role_match.group(1).strip()
            
            member = discord.utils.get(guild.members, name=user_name)
            role = discord.utils.get(guild.roles, name=role_name)
            
            if member and role:
                await member.add_roles(role)
                await message.channel.send(f"Role {role.mention} assigned to {member.mention}")
                logger.info(f"Assigned role {role_name} to {member.name}")
        return

    # BAN USER
    if "ban user" in reply_lower or "احظر" in reply_lower:
        match = re.search(r"ban user ([^\n]+)", reply, re.IGNORECASE)
        if match:
            user_name = match.group(1).strip()
            member = discord.utils.get(guild.members, name=user_name)
            
            if member:
                await member.ban(reason="AI instruction by admin")
                await message.channel.send(f"User banned: {user_name}")
                logger.warning(f"Banned user {user_name} from guild {guild.id}")
        return

    # KICK USER
    if "kick user" in reply_lower or "اطرد" in reply_lower:
        match = re.search(r"kick user ([^\n]+)", reply, re.IGNORECASE)
        if match:
            user_name = match.group(1).strip()
            member = discord.utils.get(guild.members, name=user_name)
            
            if member:
                await member.kick(reason="AI instruction by admin")
                await message.channel.send(f"User kicked: {user_name}")
                logger.warning(f"Kicked user {user_name} from guild {guild.id}")
        return

except discord.Forbidden:
    await message.channel.send("Error: I don't have permission to perform this action")
    logger.error(f"Missing permissions for admin action in guild {guild.id}")
except Exception as e:
    await message.channel.send(f"Error executing action: {str(e)}")
    logger.error(f"Error in admin action: {e}")
```

# —————————

# HOURLY DM SYSTEM WITH TASKS

# —————————

@tasks.loop(hours=1)
async def send_hourly_dms():
“”“Send hourly DM to target user.”””
user = bot.get_user(TARGET_USER_ID)
if not user:
logger.warning(f”Could not find user {TARGET_USER_ID}”)
return

```
try:
    now = datetime.datetime.now(SA_TZ)
    hour = now.hour
    
    if 5 <= hour < 12:
        greeting = "صباح الخير"
    elif 12 <= hour < 17:
        greeting = "طاب يومك"
    else:
        greeting = "مساء الخير"
    
    message = f"{greeting} <@{TARGET_USER_ID}>\nجميع البرينروتز موجودين في الحساب Guardian"
    await user.send(message)
    logger.info(f"Sent hourly DM to user {TARGET_USER_ID}")
except discord.Forbidden:
    logger.error(f"Cannot send DM to user {TARGET_USER_ID} - DMs disabled")
except Exception as e:
    logger.error(f"Error sending hourly DM: {e}")
```

@send_hourly_dms.before_loop
async def before_hourly_dms():
“”“Wait until bot is ready before starting hourly DMs.”””
await bot.wait_until_ready()

# —————————

# ON READY

# —————————

@bot.event
async def on_ready():
“”“Called when bot is ready.”””
logger.info(f”LazyAI logged in as {bot.user} (ID: {bot.user.id})”)
logger.info(f”Connected to {len(bot.guilds)} guilds”)

```
try:
    synced = await tree.sync()
    logger.info(f"Synced {len(synced)} command(s)")
except Exception as e:
    logger.error(f"Failed to sync commands: {e}")

# Start hourly DM task
if not send_hourly_dms.is_running():
    send_hourly_dms.start()
```

# —————————

# SLASH COMMANDS

# —————————

@tree.command(name=“set_prefix”, description=“Set custom bot prefix for this server”)
@app_commands.describe(prefix=“The new prefix (e.g., !, ?, lazy)”)
async def set_prefix(interaction: discord.Interaction, prefix: str):
“”“Set bot prefix for the guild.”””
if not interaction.guild:
return await interaction.response.send_message(“This command can only be used in a server”, ephemeral=True)

```
if len(prefix) > 10:
    return await interaction.response.send_message("Prefix must be 10 characters or less", ephemeral=True)

prefixes[str(interaction.guild.id)] = prefix
save_memory()
await interaction.response.send_message(f"Prefix set to `{prefix}`")
logger.info(f"Prefix set to {prefix} in guild {interaction.guild.id}")
```

@tree.command(name=“set_model”, description=“Set your personal AI model”)
@app_commands.describe(model=“Model name (e.g., LazyV.1.0)”)
async def set_model_cmd(interaction: discord.Interaction, model: str):
“”“Set user’s AI model.”””
uid = str(interaction.user.id)
user_models[uid] = model
save_memory()
await interaction.response.send_message(f”Model set to `{model}`”, ephemeral=True)
logger.info(f”User {uid} set model to {model}”)

@tree.command(name=“change_personality”, description=“Change your AI personality”)
@app_commands.describe(personality=“Personality type (e.g., friendly, professional, casual)”)
async def change_personality(interaction: discord.Interaction, personality: str):
“”“Set user’s AI personality.”””
uid = str(interaction.user.id)
user_personalities[uid] = personality
save_memory()
await interaction.response.send_message(f”Personality set to `{personality}`”, ephemeral=True)
logger.info(f”User {uid} set personality to {personality}”)

@tree.command(name=“set_autoreply_channel”, description=“Enable AI auto-reply in this channel”)
async def set_auto(interaction: discord.Interaction):
“”“Enable auto-reply in channel.”””
auto_reply_channels.add(interaction.channel_id)
save_memory()
await interaction.response.send_message(“Auto-reply enabled in this channel”)
logger.info(f”Auto-reply enabled in channel {interaction.channel_id}”)

@tree.command(name=“remove_autoreply_channel”, description=“Disable AI auto-reply in this channel”)
async def remove_auto(interaction: discord.Interaction):
“”“Disable auto-reply in channel.”””
auto_reply_channels.discard(interaction.channel_id)
save_memory()
await interaction.response.send_message(“Auto-reply disabled in this channel”)
logger.info(f”Auto-reply disabled in channel {interaction.channel_id}”)

@tree.command(name=“set_auto_reply_coding”, description=“Enable coding-focused auto-reply in this channel”)
async def set_auto_code(interaction: discord.Interaction):
“”“Enable coding auto-reply in channel.”””
coding_channels.add(interaction.channel_id)
save_memory()
await interaction.response.send_message(“Coding auto-reply enabled in this channel”)
logger.info(f”Coding auto-reply enabled in channel {interaction.channel_id}”)

@tree.command(name=“auto_reply_18”, description=“Enable adult mode in this channel (18+)”)
async def adult(interaction: discord.Interaction):
“”“Enable adult mode in channel.”””
adult_channels.add(interaction.channel_id)
save_memory()
await interaction.response.send_message(“Channel set to adult mode (18+)”, ephemeral=True)
logger.info(f”Adult mode enabled in channel {interaction.channel_id}”)

@tree.command(name=“link_whatsapp”, description=“Link your WhatsApp number”)
@app_commands.describe(phone=“Your WhatsApp phone number (with country code)”)
async def link_ws(interaction: discord.Interaction, phone: str):
“”“Link WhatsApp account.”””
uid = str(interaction.user.id)
linked_accounts[uid] = f”whatsapp:{phone}”
whatsapp_users[phone] = {
“linked_discord”: uid,
“last_interaction”: datetime.datetime.utcnow().isoformat(),
“preferred_language”: “en”,
“memory_id”: uid
}
save_memory()
await interaction.response.send_message(f”WhatsApp number {phone} linked successfully”, ephemeral=True)
logger.info(f”User {uid} linked WhatsApp {phone}”)

@tree.command(name=“clear_memory”, description=“Clear your AI conversation memory”)
async def clear(interaction: discord.Interaction):
“”“Clear user memory.”””
uid = str(interaction.user.id)
user_memory.pop(uid, None)
save_memory()
await interaction.response.send_message(“Your conversation memory has been cleared”, ephemeral=True)
logger.info(f”Cleared memory for user {uid}”)

@tree.command(name=“help”, description=“Show all available commands”)
async def help_cmd(interaction: discord.Interaction):
“”“Display help message.”””
embed = discord.Embed(
title=“LazyAI Bot Commands”,
description=“Here are all available commands:”,
color=discord.Color.blue()
)

```
embed.add_field(
    name="General Commands",
    value=(
        "`/ask` - Ask LazyAI a question\n"
        "`/help` - Show this help message\n"
        "`/clear_memory` - Clear your conversation memory"
    ),
    inline=False
)

embed.add_field(
    name="Configuration",
    value=(
        "`/set_prefix` - Set server prefix\n"
        "`/set_model` - Set your AI model\n"
        "`/change_personality` - Change AI personality"
    ),
    inline=False
)

embed.add_field(
    name="Channel Settings",
    value=(
        "`/set_autoreply_channel` - Enable auto-reply\n"
        "`/remove_autoreply_channel` - Disable auto-reply\n"
        "`/set_auto_reply_coding` - Enable coding mode\n"
        "`/auto_reply_18` - Enable adult mode (18+)"
    ),
    inline=False
)

embed.add_field(
    name="Integration",
    value="`/link_whatsapp` - Link WhatsApp number",
    inline=False
)

embed.set_footer(text="LazyAI by Xohus Interactive LLC")

await interaction.response.send_message(embed=embed, ephemeral=True)
```

# —————————

# ASK COMMAND

# —————————

@tree.command(name=“ask”, description=“Ask LazyAI a question”)
@app_commands.describe(prompt=“Your question or prompt”)
async def ask(interaction: discord.Interaction, prompt: str):
“”“Handle ask command.”””
await interaction.response.defer()

```
uid = str(interaction.user.id)
cid = interaction.channel_id
model = get_model_name(uid, cid)
personality = get_personality(uid, cid)

# Get appropriate message history
if cid in adult_channels:
    msgs = get_adult_messages(cid, uid)
else:
    msgs = user_memory.setdefault(uid, [])

# Add user message
msgs.append({"role": "user", "content": prompt})

# Query AI
reply = await query_hf(msgs, model, personality, uid)

# Add AI response to memory
msgs.append({"role": "assistant", "content": reply})

# Save memory
if cid in adult_channels:
    save_adult_memory()
else:
    save_memory()

# Send response (split if too long)
if len(reply) > 2000:
    chunks = [reply[i:i+2000] for i in range(0, len(reply), 2000)]
    await interaction.followup.send(chunks[0])
    for chunk in chunks[1:]:
        await interaction.channel.send(chunk)
else:
    await interaction.followup.send(reply)

# Execute admin actions if applicable
fake_message = type("Message", (), {
    "guild": interaction.guild,
    "author": interaction.user,
    "channel": interaction.channel
})()
await ai_execute_admin_action(fake_message, reply)
```

# —————————

# MESSAGE HANDLER

# —————————

@bot.event
async def on_message(message: discord.Message):
“”“Handle incoming messages.”””
if message.author.bot:
return

```
uid = str(message.author.id)
gid = str(message.guild.id) if message.guild else None
content = message.content

# Auto-reply channels
if message.channel.id in (adult_channels | auto_reply_channels | coding_channels):
    return await handle_ai_msg(message, content)

# Prefix handling
if gid:
    prefix = prefixes.get(gid)
    if prefix and content.startswith(prefix):
        stripped = content[len(prefix):].strip()
        if stripped:
            return await handle_ai_msg(message, stripped)

await bot.process_commands(message)
```

async def handle_ai_msg(message: discord.Message, prompt: str) -> None:
“”“Handle AI message processing.”””
uid = str(message.author.id)
cid = message.channel.id
model = get_model_name(uid, cid)
personality = get_personality(uid, cid)

```
async with message.channel.typing():
    # Get appropriate message history
    if cid in adult_channels:
        msgs = get_adult_messages(cid, uid)
        msgs.append({"role": "user", "content": prompt})
        reply = await query_hf(msgs, model, personality, uid)
        msgs.append({"role": "assistant", "content": reply})
        save_adult_memory()
    else:
        msgs = user_memory.setdefault(uid, [])
        msgs.append({"role": "user", "content": prompt})
        reply = await query_hf(msgs, model, personality, uid)
        msgs.append({"role": "assistant", "content": reply})
        save_memory()

    # Send response (split if too long)
    if len(reply) > 2000:
        chunks = [reply[i:i+2000] for i in range(0, len(reply), 2000)]
        for chunk in chunks:
            await message.channel.send(chunk)
    else:
        await message.channel.send(reply)
    
    # Execute admin actions
    await ai_execute_admin_action(message, reply)
```

# —————————

# LEGACY PREFIX COMMANDS

# —————————

@bot.command(name=“lazy”)
async def lazy_cmd(ctx: commands.Context, *, prompt: str):
“”“Legacy prefix command for asking LazyAI.”””
await handle_ai_msg(ctx.message, prompt)

@bot.command(name=“sayto”)
async def sayto(ctx: commands.Context, user: discord.User, *, text: str):
“”“Send AI response directed at specific user.”””
uid = str(ctx.author.id)
cid = ctx.channel.id
model = get_model_name(uid, cid)
personality = get_personality(uid, cid)

```
msgs = user_memory.setdefault(uid, [])
msgs.append({"role": "user", "content": text})
reply = await query_hf(msgs, model, personality, uid)
msgs.append({"role": "assistant", "content": reply})
save_memory()

await ctx.send(f"{user.mention} {reply}")
await ai_execute_admin_action(ctx.message, reply)
```

# —————————

# ERROR HANDLERS

# —————————

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
“”“Handle command errors.”””
if isinstance(error, commands.CommandNotFound):
return
elif isinstance(error, commands.MissingRequiredArgument):
await ctx.send(f”Missing required argument: {error.param.name}”)
elif isinstance(error, commands.BadArgument):
await ctx.send(f”Invalid argument: {str(error)}”)
elif isinstance(error, commands.MissingPermissions):
await ctx.send(“You don’t have permission to use this command”)
elif isinstance(error, commands.BotMissingPermissions):
await ctx.send(“I don’t have the necessary permissions to execute this command”)
else:
logger.error(f”Command error: {error}”, exc_info=error)
await ctx.send(“An error occurred while processing your command”)

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
“”“Handle slash command errors.”””
if isinstance(error, app_commands.CommandOnCooldown):
await interaction.response.send_message(
f”This command is on cooldown. Try again in {error.retry_after:.2f} seconds”,
ephemeral=True
)
elif isinstance(error, app_commands.MissingPermissions):
await interaction.response.send_message(
“You don’t have permission to use this command”,
ephemeral=True
)
elif isinstance(error, app_commands.BotMissingPermissions):
await interaction.response.send_message(
“I don’t have the necessary permissions to execute this command”,
ephemeral=True
)
else:
logger.error(f”App command error: {error}”, exc_info=error)
if not interaction.response.is_done():
await interaction.response.send_message(
“An error occurred while processing your command”,
ephemeral=True
)
else:
await interaction.followup.send(
“An error occurred while processing your command”,
ephemeral=True
)

@bot.event
async def on_error(event: str, *args, **kwargs):
“”“Handle general bot errors.”””
logger.error(f”Error in {event}”, exc_info=True)

# —————————

# GRACEFUL SHUTDOWN

# —————————

async def shutdown():
“”“Gracefully shutdown the bot.”””
logger.info(“Shutting down LazyAI bot…”)
save_memory()
save_adult_memory()
await bot.close()

# —————————

# RUN BOT

# —————————

if **name** == “**main**”:
try:
bot.run(DISCORD_TOKEN)
except KeyboardInterrupt:
logger.info(“Received keyboard interrupt”)
asyncio.run(shutdown())
except Exception as e:
logger.critical(f”Fatal error: {e}”, exc_info=True)
finally:
save_memory()
save_adult_memory()
logger.info(“Bot stopped”)
