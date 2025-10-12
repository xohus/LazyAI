import os
import discord
import aiohttp
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

@bot.event
async def on_ready():
    print(f"🧠 Lazy.AI is online as {bot.user}.")

@bot.command()
async def lazy(ctx, *, prompt: str):
    await ctx.send("🤔 Thinking...")

    payload = {
        "model": "deepseek-ai/DeepSeek-V3.2-Exp:novita",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 512
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(HF_API_URL, headers=headers, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                reply = data["choices"][0]["message"]["content"].strip()
                await ctx.send(f"🧠 {reply}")
            else:
                error_text = await resp.text()
                print(f"[ERROR] HuggingFace API status: {resp.status} - {error_text}")
                await ctx.send("⚠️ Lazy.AI is sleepy. Try again later.")

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

bot.run(DISCORD_TOKEN)
