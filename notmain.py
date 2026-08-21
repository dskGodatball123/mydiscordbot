print("=== BOT.PY START ===")

import os
from dotenv import load_dotenv

# TEMP: hard-coded token for testing
TOKEN = "MTUzOTk2NzE2MDg0NjEyMzAwOQ.GhgLHm.wtKeMbxqDx0B5rgw649NgvW1uB4SbHZxp0a-oM"
    # replace with your real token
print("DEBUG TOKEN VALUE:", repr(TOKEN))

print("Token loaded, importing discord...")
import discord
from discord import app_commands
from discord.ext import commands

print("Setting up bot...")

ALLOWED_GUILDS = {1504039403524194416}  # replace with your server ID

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

def is_allowed_guild():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild_id not in ALLOWED_GUILDS:
            await interaction.response.send_message(
                "This bot is private and cannot be used on this server.",
                ephemeral=True,
            )
            return False
        return True
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()

@bot.tree.command(name="ping")
@is_allowed_guild()
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!", ephemeral=True)

print("Starting bot.login...")
bot.run(TOKEN)