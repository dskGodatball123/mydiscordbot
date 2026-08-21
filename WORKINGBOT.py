print("=== KAGUYA BOT START ===")

import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

load_dotenv()  # reads variables from a local .env file, if present

import os
TOKEN = os.environ["DISCORD_TOKEN"] # never hardcode a real token here

ALLOWED_GUILDS = {1504039403524194416}

DB_PATH = "kaguya.db"

BRAND_NAME = "Kaguya"
CURRENCY_NAME = "Ryo"
CURRENCY_EMOJI = "🍥"
PREFIX = "!"

# Cooldowns (in seconds)
DAILY_COOLDOWN = 24 * 60 * 60   # 24 hours
WORK_COOLDOWN = 60 * 60         # 1 hour

# Original, generic ninja-rank ladder used for !rank and !profile.
RANK_TITLES = [
    (0, "Academy Student"),
    (5, "Genin"),
    (15, "Chunin"),
    (30, "Jonin"),
    (50, "Elite Jonin"),
    (75, "Shadow Operative"),
    (100, "Village Kage"),
]

# ── Summoning seal rarities (common → exclusive) ──
RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary", "exclusive"]

RARITY_INFO = {
    "common":    {"label": "Common",    "price": 200,   "color": 0x95A5A6},
    "uncommon":  {"label": "Uncommon",  "price": 500,   "color": 0x2ECC71},
    "rare":      {"label": "Rare",      "price": 1200,  "color": 0x3498DB},
    "epic":      {"label": "Epic",      "price": 3000,  "color": 0x9B59B6},
    "legendary": {"label": "Legendary", "price": 7000,  "color": 0xF1C40F},
    "exclusive": {"label": "Exclusive", "price": 15000, "color": 0xE91E63},
}

# Original companion/summon creatures — flavor only, not tied to any
# other bot's or franchise's specific named characters.
PET_CATALOG = {
    "common": [
        {"key": "ember_fox_kit", "name": "Ember Fox Kit", "emoji": "🦊", "desc": "A small fox with warm orange fur, always curious."},
        {"key": "mossy_toadling", "name": "Mossy Toadling", "emoji": "🐸", "desc": "A tiny toad that blends perfectly into forest floors."},
        {"key": "field_sparrowhawk", "name": "Field Sparrowhawk", "emoji": "🐦", "desc": "A quick little hawk used to relay village messages."},
        {"key": "loyal_pup", "name": "Loyal Pup", "emoji": "🐶", "desc": "A young tracking dog with an unshakable sense of loyalty."},
    ],
    "uncommon": [
        {"key": "shadow_wolf_pup", "name": "Shadow Wolf Pup", "emoji": "🐺", "desc": "Moves silently and prefers to travel at dusk."},
        {"key": "jade_grass_snake", "name": "Jade Grass Snake", "emoji": "🐍", "desc": "A calm, bright-green snake said to bring good fortune."},
        {"key": "stone_badger", "name": "Stone Badger", "emoji": "🦡", "desc": "Stubborn and sturdy, it digs tunnels through solid rock."},
        {"key": "river_otter_spirit", "name": "River Otter Spirit", "emoji": "🦦", "desc": "Playful and clever, at home in any stream or river."},
    ],
    "rare": [
        {"key": "storm_hawk", "name": "Storm Hawk", "emoji": "🦅", "desc": "Rides the wind ahead of incoming storms."},
        {"key": "crimson_boar", "name": "Crimson Boar", "emoji": "🐗", "desc": "Charges through obstacles without slowing down."},
        {"key": "frost_lynx", "name": "Frost Lynx", "emoji": "🐆", "desc": "Its paws never seem to feel the cold."},
        {"key": "ink_serpent", "name": "Ink Serpent", "emoji": "🐉", "desc": "Scales shimmer like wet calligraphy ink in the light."},
    ],
    "epic": [
        {"key": "thunder_panther", "name": "Thunder Panther", "emoji": "🐆", "desc": "A low rumble follows every step it takes."},
        {"key": "twilight_owl", "name": "Twilight Owl", "emoji": "🦉", "desc": "Said to see paths that others miss entirely."},
        {"key": "molten_salamander", "name": "Molten Salamander", "emoji": "🦎", "desc": "Its skin glows faintly like cooling embers."},
        {"key": "silver_fanged_wolf", "name": "Silver-Fanged Wolf", "emoji": "🐺", "desc": "A pack leader with a striking silver bite."},
    ],
    "legendary": [
        {"key": "sky_dragon_hatchling", "name": "Sky Dragon Hatchling", "emoji": "🐲", "desc": "Still learning to fly, but already commands respect."},
        {"key": "ancient_tortoise_sage", "name": "Ancient Tortoise Sage", "emoji": "🐢", "desc": "Carries the weight of centuries on its shell."},
        {"key": "golden_star_fox", "name": "Golden Star Fox", "emoji": "🦊", "desc": "Fur that catches light like scattered starlight."},
        {"key": "verdant_slug_elder", "name": "Verdant Slug Elder", "emoji": "🐌", "desc": "Slow, wise, and famed for its healing touch."},
    ],
    "exclusive": [
        {"key": "celestial_phoenix_hawk", "name": "Celestial Phoenix Hawk", "emoji": "🔥", "desc": "Wings trail faint embers wherever it soars."},
        {"key": "void_touched_serpent", "name": "Void-Touched Serpent", "emoji": "🌌", "desc": "Its scales seem to swallow the light around them."},
        {"key": "radiant_ox_spirit", "name": "Radiant Ox Spirit", "emoji": "☀️", "desc": "An immovable guardian said to bless the village gates."},
        {"key": "eclipse_wolf", "name": "Eclipse Wolf", "emoji": "🌑", "desc": "Appears only under a darkened sky, then vanishes."},
    ],
}

ALL_PETS = {pet["key"]: {**pet, "rarity": rarity} for rarity, pets in PET_CATALOG.items() for pet in pets}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


# ─────────────────────────────────────────────────────────────
# DATABASE HELPERS (sqlite3, kept simple & synchronous on purpose —
# fine for a small/medium community bot; every call is quick)
# ─────────────────────────────────────────────────────────────

def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER NOT NULL,
            guild_id    INTEGER NOT NULL,
            balance     INTEGER NOT NULL DEFAULT 0,
            xp          INTEGER NOT NULL DEFAULT 0,
            last_daily  TEXT,
            last_work   TEXT,
            wins        INTEGER NOT NULL DEFAULT 0,
            losses      INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS shop_items (
            item_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id    INTEGER NOT NULL,
            name        TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            price       INTEGER NOT NULL,
            role_id     INTEGER,
            stock       INTEGER NOT NULL DEFAULT -1,
            UNIQUE (guild_id, name)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER NOT NULL,
            guild_id  INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity  INTEGER NOT NULL DEFAULT 0,
            UNIQUE (user_id, guild_id, item_name)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_pets (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            guild_id     INTEGER NOT NULL,
            pet_key      TEXT NOT NULL,
            obtained_at  TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS level_roles (
            guild_id  INTEGER NOT NULL,
            level     INTEGER NOT NULL,
            role_id   INTEGER NOT NULL,
            PRIMARY KEY (guild_id, level)
        )
        """
    )
    conn.commit()
    conn.close()


# Default flavor items seeded into a server's shop the first time !shop
# is used there. Admins can add more (including role-granting items)
# with !shop_add.
DEFAULT_SHOP_ITEMS = [
    ("Kunai", "A standard-issue throwing blade. Every ninja carries a few.", 40),
    ("Shuriken Set", "A pouch of sharpened throwing stars.", 55),
    ("Scroll of Sealing", "A blank scroll used to seal away scrolls, tools, or summons.", 120),
    ("Soldier Pill", "Restores stamina instantly. Tastes awful.", 90),
    ("Chakra Pill", "A concentrated pill that restores a burst of chakra.", 150),
]


def seed_default_shop(guild_id: int):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM shop_items WHERE guild_id = ?", (guild_id,))
    count = cur.fetchone()["c"]
    if count == 0:
        cur.executemany(
            "INSERT INTO shop_items (guild_id, name, description, price) VALUES (?, ?, ?, ?)",
            [(guild_id, name, desc, price) for name, desc, price in DEFAULT_SHOP_ITEMS],
        )
        conn.commit()
    conn.close()


def get_shop_items(guild_id: int):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM shop_items WHERE guild_id = ? ORDER BY price ASC",
        (guild_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_shop_item(guild_id: int, name: str):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM shop_items WHERE guild_id = ? AND LOWER(name) = LOWER(?)",
        (guild_id, name),
    )
    row = cur.fetchone()
    conn.close()
    return row


def add_shop_item(guild_id: int, name: str, description: str, price: int, role_id: Optional[int], stock: int):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO shop_items (guild_id, name, description, price, role_id, stock)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(guild_id, name) DO UPDATE SET
            description = excluded.description,
            price = excluded.price,
            role_id = excluded.role_id,
            stock = excluded.stock
        """,
        (guild_id, name, description, price, role_id, stock),
    )
    conn.commit()
    conn.close()


def remove_shop_item(guild_id: int, name: str) -> bool:
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM shop_items WHERE guild_id = ? AND LOWER(name) = LOWER(?)",
        (guild_id, name),
    )
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def decrement_stock(guild_id: int, name: str):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE shop_items SET stock = stock - 1 WHERE guild_id = ? AND LOWER(name) = LOWER(?) AND stock > 0",
        (guild_id, name),
    )
    conn.commit()
    conn.close()


def add_to_inventory(user_id: int, guild_id: int, item_name: str, quantity: int = 1):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO inventory (user_id, guild_id, item_name, quantity)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, guild_id, item_name) DO UPDATE SET
            quantity = quantity + excluded.quantity
        """,
        (user_id, guild_id, item_name, quantity),
    )
    conn.commit()
    conn.close()


def get_inventory(user_id: int, guild_id: int):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM inventory WHERE user_id = ? AND guild_id = ? AND quantity > 0 ORDER BY item_name ASC",
        (user_id, guild_id),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def add_user_pet(user_id: int, guild_id: int, pet_key: str):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_pets (user_id, guild_id, pet_key, obtained_at) VALUES (?, ?, ?, ?)",
        (user_id, guild_id, pet_key, now_utc().isoformat()),
    )
    conn.commit()
    conn.close()


def get_user_pets(user_id: int, guild_id: int):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT pet_key FROM user_pets WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    )
    rows = cur.fetchall()
    conn.close()
    return [row["pet_key"] for row in rows]


def add_level_role(guild_id: int, level: int, role_id: int):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?)
        ON CONFLICT(guild_id, level) DO UPDATE SET role_id = excluded.role_id
        """,
        (guild_id, level, role_id),
    )
    conn.commit()
    conn.close()


def remove_level_role(guild_id: int, level: int) -> bool:
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM level_roles WHERE guild_id = ? AND level = ?", (guild_id, level))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_level_roles(guild_id: int):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM level_roles WHERE guild_id = ? ORDER BY level ASC", (guild_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_level_roles_between(guild_id: int, low_level: int, high_level: int):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM level_roles WHERE guild_id = ? AND level > ? AND level <= ? ORDER BY level ASC",
        (guild_id, low_level, high_level),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_user_row(user_id: int, guild_id: int) -> sqlite3.Row:
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    )
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO users (user_id, guild_id) VALUES (?, ?)",
            (user_id, guild_id),
        )
        conn.commit()
        cur.execute(
            "SELECT * FROM users WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        row = cur.fetchone()
    conn.close()
    return row


def update_user(user_id: int, guild_id: int, **fields):
    if not fields:
        return
    get_user_row(user_id, guild_id)  # make sure the row exists
    conn = db_connect()
    cur = conn.cursor()
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [user_id, guild_id]
    cur.execute(
        f"UPDATE users SET {set_clause} WHERE user_id = ? AND guild_id = ?",
        values,
    )
    conn.commit()
    conn.close()


def add_balance(user_id: int, guild_id: int, amount: int):
    row = get_user_row(user_id, guild_id)
    new_balance = max(0, row["balance"] + amount)
    update_user(user_id, guild_id, balance=new_balance)
    return new_balance


def add_xp(user_id: int, guild_id: int, amount: int):
    row = get_user_row(user_id, guild_id)
    new_xp = row["xp"] + amount
    update_user(user_id, guild_id, xp=new_xp)
    return new_xp


def top_users(guild_id: int, limit: int = 10):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE guild_id = ? ORDER BY balance DESC LIMIT ?",
        (guild_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ─────────────────────────────────────────────────────────────
# SMALL UTILITIES
# ─────────────────────────────────────────────────────────────

def rank_title_for_level(level: int) -> str:
    title = RANK_TITLES[0][1]
    for threshold, name in RANK_TITLES:
        if level >= threshold:
            title = name
        else:
            break
    return title


def level_from_xp(xp: int) -> int:
    # Simple, predictable curve: 100 xp per level.
    return xp // 100


def xp_progress(xp: int):
    level = level_from_xp(xp)
    current_level_xp = xp - (level * 100)
    return level, current_level_xp, 100


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def format_timedelta(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def kaguya_embed(title: str, description: str = "", color: int = 0x8E44AD) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=BRAND_NAME)
    return embed


# ─────────────────────────────────────────────────────────────
# GUILD CHECK
# ─────────────────────────────────────────────────────────────

def is_allowed_guild():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None or ctx.guild.id not in ALLOWED_GUILDS:
            await ctx.send("This bot is private and cannot be used on this server.")
            return False
        return True
    return commands.check(predicate)


class OptionalRoleConverter(commands.Converter):
    """Lets a user type a role mention/name, or 'none' to skip it."""
    async def convert(self, ctx: commands.Context, argument: str):
        if argument.lower() in ("none", "skip", "-"):
            return None
        return await commands.RoleConverter().convert(ctx, argument)


async def handle_level_up(ctx: commands.Context, user_id: int, guild_id: int, old_level: int, new_level: int):
    title = rank_title_for_level(new_level)
    embed = kaguya_embed(
        "Level Up!",
        f"{ctx.author.mention} reached **Level {new_level}** — {title}!",
        color=0xF1C40F,
    )
    await ctx.send(embed=embed)

    for role_row in get_level_roles_between(guild_id, old_level, new_level):
        role = ctx.guild.get_role(role_row["role_id"])
        if role is None:
            continue
        try:
            await ctx.author.add_roles(role, reason="Kaguya level-up reward")
            await ctx.send(embed=kaguya_embed(
                "Role Unlocked",
                f"You've been granted **{role.name}** for reaching level {role_row['level']}!",
                color=0x2ECC71,
            ))
        except discord.Forbidden:
            await ctx.send(f"(Couldn't grant **{role.name}** — check the bot's role permissions/position.)")


async def grant_xp(ctx: commands.Context, user_id: int, guild_id: int, amount: int):
    row = get_user_row(user_id, guild_id)
    old_level, _, _ = xp_progress(row["xp"])
    new_xp = add_xp(user_id, guild_id, amount)
    new_level, _, _ = xp_progress(new_xp)
    if new_level > old_level:
        await handle_level_up(ctx, user_id, guild_id, old_level, new_level)


# ─────────────────────────────────────────────────────────────
# EVENTS
# ─────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    init_db()
    print("Database ready.")
    print(f"=== {BRAND_NAME.upper()} BOT READY (prefix: {PREFIX}) ===")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Slow down! Try again in {error.retry_after:.1f}s.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You need Administrator permission to use this command.")
    elif isinstance(error, commands.CheckFailure):
        # Guild-restriction check already sent its own message.
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing an argument: `{error.param.name}`. Check `!help` for usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"That didn't look right: {error}")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        await ctx.send("Something went wrong running that command.")
        print(f"Command error: {error}")


# ─────────────────────────────────────────────────────────────
# COMMAND: !kaguya_ping (kept from the original bot)
# ─────────────────────────────────────────────────────────────

@bot.command(name="kaguya_ping")
@is_allowed_guild()
async def ping_command(ctx: commands.Context):
    await ctx.send("Pong!")


# ─────────────────────────────────────────────────────────────
# COMMAND: !help
# ─────────────────────────────────────────────────────────────

@bot.command(name="help")
@is_allowed_guild()
async def help_command(ctx: commands.Context):
    embed = kaguya_embed(
        f"{BRAND_NAME} — Command Guide",
        "Here's everything you can do around the village:",
    )
    embed.add_field(
        name="General",
        value=(
            "`!kaguya_ping` — check if the bot is alive\n"
            "`!help` — show this menu\n"
            "`!profile` — view your ninja profile\n"
            "`!rank` — check your level & progress"
        ),
        inline=False,
    )
    embed.add_field(
        name="Economy",
        value=(
            f"`!balance` — check your {CURRENCY_NAME}\n"
            f"`!daily` — claim a daily {CURRENCY_NAME} reward\n"
            f"`!work` — complete a mission for {CURRENCY_NAME}\n"
            "`!leaderboard` — see the richest ninja in the village"
        ),
        inline=False,
    )
    embed.add_field(
        name="Games",
        value=(
            "`!guess <1-10>` — guess a hidden number to win Ryo\n"
            "`!roll <bet>` — bet Ryo on a dice roll"
        ),
        inline=False,
    )
    embed.add_field(
        name="Shop",
        value=(
            "`!shop` — browse items for sale in the village\n"
            "`!buy <item name>` — purchase an item with your Ryo\n"
            "`!inventory` — view items you own\n"
            "`!shop_add \"Name\" price stock role_or_none description...` — *(admin)*\n"
            "`!shop_remove <item name>` — *(admin)*"
        ),
        inline=False,
    )
    embed.add_field(
        name="Pets & Summoning Seals",
        value=(
            "`!seals` — view seal tiers, prices & pool sizes\n"
            "`!buy_seal <tier>` — buy a seal and summon a pet (common → exclusive)\n"
            "`!pets` — view the pets you own\n"
            "`!compendium` — see every pet and which you've unlocked"
        ),
        inline=False,
    )
    embed.add_field(
        name="Leveling & Roles",
        value=(
            "`!levelroles` — view level → role rewards\n"
            "`!levelrole_add <level> <role>` — *(admin)* set a role reward\n"
            "`!levelrole_remove <level>` — *(admin)* remove a role reward"
        ),
        inline=False,
    )
    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────
# COMMAND: !profile
# ─────────────────────────────────────────────────────────────

@bot.command(name="profile")
@is_allowed_guild()
async def profile_command(ctx: commands.Context):
    user = ctx.author
    row = get_user_row(user.id, ctx.guild.id)
    level, current_xp, needed_xp = xp_progress(row["xp"])
    title = rank_title_for_level(level)

    embed = kaguya_embed(f"{user.display_name}'s Profile")
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Rank", value=title, inline=True)
    embed.add_field(name="Level", value=str(level), inline=True)
    embed.add_field(name="XP", value=f"{current_xp}/{needed_xp}", inline=True)
    embed.add_field(name="Balance", value=f"{row['balance']} {CURRENCY_EMOJI} {CURRENCY_NAME}", inline=True)
    embed.add_field(name="Wins", value=str(row["wins"]), inline=True)
    embed.add_field(name="Losses", value=str(row["losses"]), inline=True)
    embed.add_field(name="Pets Owned", value=str(len(get_user_pets(user.id, ctx.guild.id))), inline=True)

    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────
# COMMAND: !balance
# ─────────────────────────────────────────────────────────────

@bot.command(name="balance")
@is_allowed_guild()
async def balance_command(ctx: commands.Context):
    row = get_user_row(ctx.author.id, ctx.guild.id)
    embed = kaguya_embed(
        "Balance",
        f"You have **{row['balance']} {CURRENCY_EMOJI} {CURRENCY_NAME}**.",
    )
    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────
# COMMAND: !daily
# ─────────────────────────────────────────────────────────────

@bot.command(name="daily")
@is_allowed_guild()
async def daily_command(ctx: commands.Context):
    user_id, guild_id = ctx.author.id, ctx.guild.id
    row = get_user_row(user_id, guild_id)

    if row["last_daily"]:
        last_claim = parse_iso(row["last_daily"])
        elapsed = now_utc() - last_claim
        if elapsed.total_seconds() < DAILY_COOLDOWN:
            remaining = timedelta(seconds=DAILY_COOLDOWN) - elapsed
            embed = kaguya_embed(
                "Daily Reward",
                f"You've already claimed today's reward. Come back in **{format_timedelta(remaining)}**.",
                color=0xE67E22,
            )
            await ctx.send(embed=embed)
            return

    reward = random.randint(150, 300)
    new_balance = add_balance(user_id, guild_id, reward)
    await grant_xp(ctx, user_id, guild_id, 10)
    update_user(user_id, guild_id, last_daily=now_utc().isoformat())

    embed = kaguya_embed(
        "Daily Reward Claimed!",
        f"You received **{reward} {CURRENCY_EMOJI} {CURRENCY_NAME}**.\nNew balance: **{new_balance}**.",
        color=0x2ECC71,
    )
    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────
# COMMAND: !work
# ─────────────────────────────────────────────────────────────

WORK_FLAVOR = [
    "delivered scrolls across the village",
    "helped repair the academy walls",
    "escorted a merchant caravan safely",
    "trained new recruits at the academy",
    "gathered herbs for the hospital",
    "patrolled the village gates",
    "assisted a local shop for the day",
]

@bot.command(name="work")
@is_allowed_guild()
async def work_command(ctx: commands.Context):
    user_id, guild_id = ctx.author.id, ctx.guild.id
    row = get_user_row(user_id, guild_id)

    if row["last_work"]:
        last_work = parse_iso(row["last_work"])
        elapsed = now_utc() - last_work
        if elapsed.total_seconds() < WORK_COOLDOWN:
            remaining = timedelta(seconds=WORK_COOLDOWN) - elapsed
            embed = kaguya_embed(
                "Still Tired",
                f"You need to rest before your next mission. Try again in **{format_timedelta(remaining)}**.",
                color=0xE67E22,
            )
            await ctx.send(embed=embed)
            return

    reward = random.randint(50, 120)
    flavor = random.choice(WORK_FLAVOR)
    new_balance = add_balance(user_id, guild_id, reward)
    await grant_xp(ctx, user_id, guild_id, 5)
    update_user(user_id, guild_id, last_work=now_utc().isoformat())

    embed = kaguya_embed(
        "Mission Complete",
        f"You {flavor} and earned **{reward} {CURRENCY_EMOJI} {CURRENCY_NAME}**.\nNew balance: **{new_balance}**.",
        color=0x2ECC71,
    )
    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────
# COMMAND: !rank
# ─────────────────────────────────────────────────────────────

@bot.command(name="rank")
@is_allowed_guild()
async def rank_command(ctx: commands.Context):
    row = get_user_row(ctx.author.id, ctx.guild.id)
    level, current_xp, needed_xp = xp_progress(row["xp"])
    title = rank_title_for_level(level)

    bar_length = 20
    filled = int(bar_length * (current_xp / needed_xp))
    bar = "█" * filled + "░" * (bar_length - filled)

    embed = kaguya_embed(
        f"{ctx.author.display_name}'s Rank",
        f"**{title}** — Level {level}\n`{bar}` {current_xp}/{needed_xp} XP",
    )
    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────
# COMMAND: !leaderboard
# ─────────────────────────────────────────────────────────────

@bot.command(name="leaderboard")
@is_allowed_guild()
async def leaderboard_command(ctx: commands.Context):
    rows = top_users(ctx.guild.id, limit=10)

    if not rows:
        await ctx.send("No one has any Ryo yet!")
        return

    lines = []
    for i, row in enumerate(rows, start=1):
        member = ctx.guild.get_member(row["user_id"])
        name = member.display_name if member else f"User {row['user_id']}"
        lines.append(f"**#{i}** — {name}: {row['balance']} {CURRENCY_EMOJI}")

    embed = kaguya_embed("Village Leaderboard", "\n".join(lines))
    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────
# COMMAND: !guess (mini-game)
# ─────────────────────────────────────────────────────────────

@bot.command(name="guess")
@commands.cooldown(1, 15, commands.BucketType.user)
@is_allowed_guild()
async def guess_command(ctx: commands.Context, number: int):
    if not (1 <= number <= 10):
        await ctx.send("Please guess a number between 1 and 10, e.g. `!guess 7`.")
        return

    user_id, guild_id = ctx.author.id, ctx.guild.id
    secret = random.randint(1, 10)

    if number == secret:
        reward = 200
        add_balance(user_id, guild_id, reward)
        await grant_xp(ctx, user_id, guild_id, 15)
        update_user(user_id, guild_id, wins=get_user_row(user_id, guild_id)["wins"] + 1)
        embed = kaguya_embed(
            "Correct!",
            f"The number was **{secret}**. You win **{reward} {CURRENCY_EMOJI} {CURRENCY_NAME}**!",
            color=0x2ECC71,
        )
    else:
        update_user(user_id, guild_id, losses=get_user_row(user_id, guild_id)["losses"] + 1)
        embed = kaguya_embed(
            "Not Quite",
            f"The number was **{secret}**. Better luck next time!",
            color=0xE74C3C,
        )

    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────
# COMMAND: !roll (mini-game)
# ─────────────────────────────────────────────────────────────

@bot.command(name="roll")
@commands.cooldown(1, 15, commands.BucketType.user)
@is_allowed_guild()
async def roll_command(ctx: commands.Context, bet: int):
    if bet < 1:
        await ctx.send("Bet at least 1 Ryo, e.g. `!roll 50`.")
        return

    user_id, guild_id = ctx.author.id, ctx.guild.id
    row = get_user_row(user_id, guild_id)

    if bet > row["balance"]:
        await ctx.send(f"You don't have enough {CURRENCY_NAME} for that bet. Your balance: {row['balance']}.")
        return

    dice_result = random.randint(1, 6)

    if dice_result >= 4:
        winnings = bet
        add_balance(user_id, guild_id, winnings)
        await grant_xp(ctx, user_id, guild_id, 8)
        update_user(user_id, guild_id, wins=row["wins"] + 1)
        embed = kaguya_embed(
            "You Win!",
            f"🎲 You rolled a **{dice_result}**.\nYou won **{winnings} {CURRENCY_EMOJI} {CURRENCY_NAME}**!",
            color=0x2ECC71,
        )
    else:
        add_balance(user_id, guild_id, -bet)
        update_user(user_id, guild_id, losses=row["losses"] + 1)
        embed = kaguya_embed(
            "You Lose",
            f"🎲 You rolled a **{dice_result}**.\nYou lost **{bet} {CURRENCY_EMOJI} {CURRENCY_NAME}**.",
            color=0xE74C3C,
        )

    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────
# PET & SUMMONING SEAL SYSTEM
# ─────────────────────────────────────────────────────────────

@bot.command(name="seals")
@is_allowed_guild()
async def seals_command(ctx: commands.Context):
    embed = kaguya_embed(
        "Summoning Seals",
        "Buy a seal to summon a companion of that rarity. Higher tiers cost more but hold rarer pets.",
    )
    for tier in RARITY_ORDER:
        info = RARITY_INFO[tier]
        pool_size = len(PET_CATALOG[tier])
        embed.add_field(
            name=f"{info['label']} Seal — {info['price']} {CURRENCY_EMOJI}",
            value=f"`!buy_seal {tier}` • {pool_size} possible pets",
            inline=False,
        )
    await ctx.send(embed=embed)


@bot.command(name="buy_seal")
@is_allowed_guild()
async def buy_seal_command(ctx: commands.Context, tier: str):
    tier = tier.lower()
    if tier not in RARITY_INFO:
        valid = ", ".join(RARITY_ORDER)
        await ctx.send(f"Unknown seal tier. Choose one of: {valid}")
        return

    user_id, guild_id = ctx.author.id, ctx.guild.id
    price = RARITY_INFO[tier]["price"]
    row = get_user_row(user_id, guild_id)

    if row["balance"] < price:
        await ctx.send(f"You need {price} {CURRENCY_EMOJI} for a {RARITY_INFO[tier]['label']} Seal, but only have {row['balance']}.")
        return

    add_balance(user_id, guild_id, -price)
    pet = random.choice(PET_CATALOG[tier])
    add_user_pet(user_id, guild_id, pet["key"])
    await grant_xp(ctx, user_id, guild_id, 10)

    embed = kaguya_embed(
        f"{RARITY_INFO[tier]['label']} Seal Opened!",
        f"{pet['emoji']} You summoned **{pet['name']}**!\n*{pet['desc']}*",
        color=RARITY_INFO[tier]["color"],
    )
    await ctx.send(embed=embed)


@bot.command(name="pets")
@is_allowed_guild()
async def pets_command(ctx: commands.Context):
    pet_keys = get_user_pets(ctx.author.id, ctx.guild.id)

    if not pet_keys:
        await ctx.send("You don't have any pets yet. Try `!seals` to get started!")
        return

    counts = {}
    for key in pet_keys:
        counts[key] = counts.get(key, 0) + 1

    embed = kaguya_embed(f"{ctx.author.display_name}'s Pets", f"Total: {len(pet_keys)}")
    for tier in RARITY_ORDER:
        owned_in_tier = [
            f"{ALL_PETS[key]['emoji']} {ALL_PETS[key]['name']} x{count}"
            for key, count in counts.items()
            if ALL_PETS[key]["rarity"] == tier
        ]
        if owned_in_tier:
            embed.add_field(name=RARITY_INFO[tier]["label"], value="\n".join(owned_in_tier), inline=False)

    await ctx.send(embed=embed)


@bot.command(name="compendium")
@is_allowed_guild()
async def compendium_command(ctx: commands.Context):
    owned_keys = set(get_user_pets(ctx.author.id, ctx.guild.id))

    embed = kaguya_embed(
        "Village Compendium",
        "Every companion known to the village. Unowned pets are hidden as `???`.",
    )
    for tier in RARITY_ORDER:
        lines = []
        for pet in PET_CATALOG[tier]:
            if pet["key"] in owned_keys:
                lines.append(f"{pet['emoji']} {pet['name']}")
            else:
                lines.append("❔ ???")
        embed.add_field(name=RARITY_INFO[tier]["label"], value="\n".join(lines), inline=True)

    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────
# LEVEL ROLES
# ─────────────────────────────────────────────────────────────

@bot.command(name="levelroles")
@is_allowed_guild()
async def levelroles_command(ctx: commands.Context):
    rows = get_level_roles(ctx.guild.id)

    if not rows:
        await ctx.send("No level-role rewards are set up yet.")
        return

    lines = []
    for row in rows:
        role = ctx.guild.get_role(row["role_id"])
        role_text = role.mention if role else f"(missing role id {row['role_id']})"
        lines.append(f"Level {row['level']} → {role_text}")

    embed = kaguya_embed("Level Role Rewards", "\n".join(lines))
    await ctx.send(embed=embed)


@bot.command(name="levelrole_add")
@commands.has_permissions(administrator=True)
@is_allowed_guild()
async def levelrole_add_command(ctx: commands.Context, level: int, role: discord.Role):
    if level < 1:
        await ctx.send("Level must be at least 1.")
        return

    add_level_role(ctx.guild.id, level, role.id)
    embed = kaguya_embed(
        "Level Role Set",
        f"Members will now receive {role.mention} upon reaching **Level {level}**.",
        color=0x2ECC71,
    )
    await ctx.send(embed=embed)


@bot.command(name="levelrole_remove")
@commands.has_permissions(administrator=True)
@is_allowed_guild()
async def levelrole_remove_command(ctx: commands.Context, level: int):
    removed = remove_level_role(ctx.guild.id, level)
    if removed:
        await ctx.send(f"Removed the role reward for level {level}.")
    else:
        await ctx.send(f"No role reward was set for level {level}.")


# ─────────────────────────────────────────────────────────────
# SHOP SYSTEM
# ─────────────────────────────────────────────────────────────

@bot.command(name="shop")
@is_allowed_guild()
async def shop_command(ctx: commands.Context):
    seed_default_shop(ctx.guild.id)
    items = get_shop_items(ctx.guild.id)

    if not items:
        await ctx.send("The shop is empty right now.")
        return

    embed = kaguya_embed(
        "Village Shop",
        "Spend your Ryo on gear, keepsakes, and village honors.",
    )
    for item in items:
        stock_text = "Unlimited" if item["stock"] < 0 else str(item["stock"])
        role_text = " • Grants a role" if item["role_id"] else ""
        embed.add_field(
            name=f"{item['name']} — {item['price']} {CURRENCY_EMOJI}",
            value=f"{item['description']}\nStock: {stock_text}{role_text}",
            inline=False,
        )

    await ctx.send(embed=embed)


@bot.command(name="buy")
@is_allowed_guild()
async def buy_command(ctx: commands.Context, *, item: str):
    user_id, guild_id = ctx.author.id, ctx.guild.id
    shop_item = get_shop_item(guild_id, item)

    if shop_item is None:
        await ctx.send(f"No item called **{item}** was found in the shop. Check `!shop` for the current list.")
        return

    if shop_item["stock"] == 0:
        await ctx.send(f"**{shop_item['name']}** is out of stock.")
        return

    row = get_user_row(user_id, guild_id)
    if row["balance"] < shop_item["price"]:
        await ctx.send(f"You need {shop_item['price']} {CURRENCY_EMOJI} but only have {row['balance']}.")
        return

    add_balance(user_id, guild_id, -shop_item["price"])
    decrement_stock(guild_id, shop_item["name"])

    role_note = ""
    if shop_item["role_id"]:
        role = ctx.guild.get_role(shop_item["role_id"])
        if role is not None:
            try:
                await ctx.author.add_roles(role, reason="Kaguya shop purchase")
                role_note = f"\nYou've been granted the **{role.name}** role."
            except discord.Forbidden:
                role_note = "\n(Couldn't assign the role — check the bot's role permissions.)"
        else:
            add_to_inventory(user_id, guild_id, shop_item["name"], 1)
    else:
        add_to_inventory(user_id, guild_id, shop_item["name"], 1)

    embed = kaguya_embed(
        "Purchase Complete",
        f"You bought **{shop_item['name']}** for **{shop_item['price']} {CURRENCY_EMOJI}**.{role_note}",
        color=0x2ECC71,
    )
    await ctx.send(embed=embed)


@bot.command(name="inventory")
@is_allowed_guild()
async def inventory_command(ctx: commands.Context):
    rows = get_inventory(ctx.author.id, ctx.guild.id)

    if not rows:
        await ctx.send("Your inventory is empty. Try `!shop` and `!buy`!")
        return

    lines = [f"**{row['item_name']}** x{row['quantity']}" for row in rows]
    embed = kaguya_embed(f"{ctx.author.display_name}'s Inventory", "\n".join(lines))
    await ctx.send(embed=embed)


@bot.command(name="shop_add")
@commands.has_permissions(administrator=True)
@is_allowed_guild()
async def shop_add_command(
    ctx: commands.Context,
    name: str,
    price: int,
    stock: int,
    role: OptionalRoleConverter,
    *,
    description: str,
):
    """
    Usage: !shop_add "Item Name" price stock role_or_none description...
    Example: !shop_add "Leaf Headband" 500 -1 @Genin Grants the Genin rank and headband!
    Use -1 for unlimited stock, and 'none' if the item shouldn't grant a role.
    """
    if price < 1:
        await ctx.send("Price must be at least 1.")
        return

    role_id = role.id if role else None
    add_shop_item(ctx.guild.id, name, description, price, role_id, stock)

    embed = kaguya_embed(
        "Shop Updated",
        f"**{name}** is now available for **{price} {CURRENCY_EMOJI}**.",
        color=0x2ECC71,
    )
    if role:
        embed.add_field(name="Grants Role", value=role.mention, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="shop_remove")
@commands.has_permissions(administrator=True)
@is_allowed_guild()
async def shop_remove_command(ctx: commands.Context, *, item: str):
    removed = remove_shop_item(ctx.guild.id, item)
    if removed:
        await ctx.send(f"Removed **{item}** from the shop.")
    else:
        await ctx.send(f"No item called **{item}** was found.")


# ─────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────

bot.run(TOKEN)