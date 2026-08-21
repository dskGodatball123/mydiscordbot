print("=== BOT START ===")

import discord
from discord import app_commands
from discord.ext import commands

# Use the SAME token that worked in test_bot.py
TOKEN = "MTUzOTk2NzE2MDg0NjEyMzAwOQ.G_6ODh.bv1_TPO5lcaGF7eB-8oYPTtK7vy09p8m8UMyEw"  # replace with the token that logged in as Kaguya#3072

# Replace with your actual server ID
ALLOWED_GUILDS = {1504039403524194416}

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
    print("=== BOT READY ===")

@bot.tree.command(name="ping")
@is_allowed_guild()
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!", ephemeral=True)

bot.run(TOKEN)