import discord
import aiohttp
import os
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# Config
HF_API_URL = "https://api-inference.huggingface.co/models/deepseek-ai/DeepSeek-V3.2-Exp"
HEADERS = { "Authorization": f"Bearer {HF_TOKEN}" }

# Runtime storage
auto_reply_channels = set()
custom_prefixes = set(["!lazy", "hey lazy", "l!lazy", ","])  # default triggers

# Setup bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🧠 Lazy.AI is online as {bot.user}.")

@bot.command()
async def lazy(ctx, *, prompt: str):
    """Ask Lazy.AI something."""
    await ctx.send("🤔 Thinking...")
    response = await ask_huggingface(prompt)
    if response:
        await ctx.send(f"🧠 {response}")
    else:
        await ctx.send("⚠️ Lazy.AI is sleepy. Try again later.")

@bot.command()
async def add_auto_reply_channel(ctx):
    """Adds this channel for passive Lazy.AI replies (no command needed)."""
    auto_reply_channels.add(ctx.channel.id)
    await ctx.send("✅ Added this channel to auto-reply list.")

@bot.command()
async def add_reply_prefix(ctx, *, prefix: str):
    """Adds a new trigger prefix like 'hey lazy'."""
    custom_prefixes.add(prefix.lower())
    await ctx.send(f"✅ Added prefix: `{prefix}`")

@bot.command()
async def help_lazy(ctx):
    """Shows help message."""
    help_text = (
        "**🧠 Lazy.AI Commands:**\n"
        "`!lazy [question]` – Ask something directly\n"
        "`!add_auto_reply_channel` – Auto-reply in this channel\n"
        "`!add_reply_prefix [text]` – Add prefix to trigger AI\n"
        "`!help_lazy` – Show this help message\n\n"
        "**Passive Mode:**\n"
        "If you say things like `hey lazy` or `,`, it'll respond if enabled."
    )
    await ctx.send(help_text)

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

@bot.event
async def on_message(message):
    # Skip bot’s own messages
    if message.author.bot:
        return

    # Passive reply based on channel or prefix
    content = message.content.lower().strip()
    if (message.channel.id in auto_reply_channels) or any(content.startswith(p) for p in custom_prefixes):
        prompt = content
        await message.channel.send("🤔 Thinking...")
        response = await ask_huggingface(prompt)
        if response:
            await message.channel.send(f"🧠 {response}")
        else:
            await message.channel.send("⚠️ Lazy.AI is sleepy. Try again later.")

    await bot.process_commands(message)

async def ask_huggingface(prompt):
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 1024,
            "temperature": 0.7
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(HF_API_URL, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                text = data.get("generated_text", "")
                return text.replace(prompt, "").strip()
            return None

bot.run(DISCORD_TOKEN)
