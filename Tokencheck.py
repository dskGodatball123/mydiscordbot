print("=== TOKEN CHECK ===")

TOKEN = "MTUzOTk2NzE2MDg0NjEyMzAwOQ.GK8v5i.jTMHsfdK7g15OIIXJSm_8lIRTBD-1lTwM38vZo"  # replace with the token you just copied

print("TOKEN LENGTH:", len(TOKEN))
print("TOKEN START:", TOKEN[:10])
print("TOKEN END:", TOKEN[-10:])

import discord

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    print("=== TOKEN OK ===")
    await client.close()

client.run(TOKEN)