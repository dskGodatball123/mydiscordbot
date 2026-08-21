print("=== BOT FINAL START ===")

import discord
from discord import app_commands
from discord.ext import commands

# PASTE YOUR FRESH TOKEN BELOW, INSIDE THE QUOTES
TOKEN = "MTUzOTk2NzE2MDg0NjEyMzAwOQ.G_6ODh.bv1_TPO5lcaGF7eB-8oYPTtK7vy09p8m8UMyEw"

# Replace with your server ID
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
    print("=== BOT READY ===")

@bot.tree.command(name="ping")
@is_allowed_guild()
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!", ephemeral=True)

print("TOKEN LENGTH:", len(TOKEN))
print("TOKEN START:", TOKEN[:10])
print("TOKEN END:", TOKEN[-10:])

bot.run(TOKEN)