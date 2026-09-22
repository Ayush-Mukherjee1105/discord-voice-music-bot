import os

from dotenv import load_dotenv


load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing. "
        "Make sure it is set in the .env file."
    )

if not DISCORD_GUILD_ID:
    raise RuntimeError(
        "DISCORD_GUILD_ID is missing. "
        "Make sure it is set in the .env file."
    )

try:
    DISCORD_GUILD_ID = int(DISCORD_GUILD_ID)

except ValueError:
    raise RuntimeError(
        "DISCORD_GUILD_ID must be a valid Discord server ID."
    )