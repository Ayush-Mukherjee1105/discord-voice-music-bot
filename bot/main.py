import asyncio

import discord
from discord.ext import commands

from bot.utils.config import DISCORD_TOKEN


# --------------------------------------------------
# Discord intents
# --------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True


# --------------------------------------------------
# Bot
# --------------------------------------------------

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=commands.DefaultHelpCommand()
)


# --------------------------------------------------
# Events
# --------------------------------------------------

@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("Discord bot is online.")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"Missing argument: `{error.param.name}`."
        )
        return

    if isinstance(error, commands.CommandInvokeError):
        print(
            f"Command error in `{ctx.command}`: "
            f"{type(error.original).__name__}: {error.original}"
        )
        await ctx.send(
            "Something went wrong while executing that command."
        )
        return

    print(
        f"Command error in `{ctx.command}`: "
        f"{type(error).__name__}: {error}"
    )


# --------------------------------------------------
# Extensions
# --------------------------------------------------

def load_extensions():
    bot.load_extension("bot.commands.general")
    bot.load_extension("bot.commands.music")


# --------------------------------------------------
# Main
# --------------------------------------------------

async def main():
    load_extensions()

    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())