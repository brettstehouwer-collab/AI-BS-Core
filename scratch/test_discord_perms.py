import os
import asyncio
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

token = ""
with open(r"C:\AI-BS\.env", "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("DISCORD_BOT_TOKEN="):
            token = line.split("=", 1)[1].strip().strip('"').strip("'")

@bot.event
async def on_ready():
    print(f"Bot logged in as: {bot.user}")
    ch = bot.get_channel(1526361931399827466)
    print(f"Channel 1526361931399827466 found: {ch is not None}")
    if ch:
        print(f"Channel name: {ch.name}")
        perms = ch.permissions_for(ch.guild.me)
        print(f"Can send messages: {perms.send_messages}")
        print(f"Can embed links: {perms.embed_links}")
    await bot.close()

if token:
    bot.run(token)
else:
    print("No token found.")
