import os
import discord
import aiohttp
from discord.ext import commands
from dotenv import load_dotenv
from langdetect import detect

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

HF_API_URL = "https://router.huggingface.co/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
}

# User memory for context
user_context = {}

# Default prefix list per user/server
prefixes = {}
auto_reply_channels = set()

@bot.event
async def on_ready():
    print(f"🧠 LazyAI is online as {bot.user}.")

# --- Utility: Language Detection
def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

# --- Utility: Format response
def clean_response(raw, prompt):
    try:
        response = raw["choices"][0]["message"]["content"]
        return response.replace(prompt, "").replace("DeepSeek", "LazyAI").strip()
    except:
        return "⚠️ LazyAI couldn’t understand the reply."

# --- Main AI Query
async def get_lazyai_reply(user_id, prompt):
    history = user_context.get(user_id, [])
    history.append({"role": "user", "content": prompt})

    payload = {
        "model": "deepseek-ai/DeepSeek-V3.2-Exp:novita",
        "messages": history[-10:]  # Limit context
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(HF_API_URL, headers=headers, json=payload) as resp:
            if resp.status == 200:
                raw = await resp.json()
                reply = clean_response(raw, prompt)
                user_context[user_id] = history + [{"role": "assistant", "content": reply}]
                return reply
            else:
                error = await resp.text()
                return f"⚠️ LazyAI is sleepy. Try again later.\n`[ERROR] HuggingFace API status: {resp.status} - {error}`"

# --- Handle Messages Automatically
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    channel_id = str(message.channel.id)

    text = message.content.strip()
    lang = detect_language(text)

    # Auto-reply channel logic
    if channel_id in auto_reply_channels or any(text.lower().startswith(p) for p in prefixes.get(channel_id, [])):
        reply = await get_lazyai_reply(user_id, text)
        await message.channel.send(reply)
    else:
        await bot.process_commands(message)

# --- Slash Command: /set-autoreply-channel
@bot.command(name="set-autoreply-channel")
async def set_autoreply_channel(ctx):
    auto_reply_channels.add(str(ctx.channel.id))
    await ctx.send("✅ LazyAI will now auto-reply in this channel.")

# --- Slash Command: /set-prefix
@bot.command(name="set-prefix")
async def set_prefix(ctx, *, prefix: str):
    cid = str(ctx.channel.id)
    if cid not in prefixes:
        prefixes[cid] = []
    prefixes[cid].append(prefix.lower())
    await ctx.send(f"✅ LazyAI will now respond to messages starting with: `{prefix}`")

# --- Slash Command: /help
@bot.command(name="help")
async def help_command(ctx):
    help_msg = (
        "**🧠 LazyAI Command List**\n"
        "`/set-autoreply-channel` — Let LazyAI auto-reply to any message in this channel.\n"
        "`/set-prefix <word>` — Let LazyAI respond when a message starts with this prefix.\n"
        "`!lazy <question>` — Manually ask LazyAI something.\n"
        "`!ping` — Check if LazyAI is awake.\n"
        "`/help` — Show this message.\n\n"
        "LazyAI will remember what you say in this channel and respond naturally, even in Arabic or other languages."
    )
    await ctx.send(help_msg)

# --- Ping Test
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("🏓 Pong! LazyAI is alive.")

# --- Manual Ask
@bot.command(name="lazy")
async def lazy(ctx, *, prompt: str):
    user_id = str(ctx.author.id)
    await ctx.send("🤔 LazyAI is thinking...")
    reply = await get_lazyai_reply(user_id, prompt)
    await ctx.send(reply)

# --- Mention Handler
@bot.command(name="sayto")
async def say_to(ctx, user: discord.User, *, message: str):
    mention = f"<@{user.id}>"
    reply = await get_lazyai_reply(str(ctx.author.id), message)
    await ctx.send(f"{mention} 🧠 LazyAI says:\n{reply}")

bot.run(DISCORD_TOKEN)
