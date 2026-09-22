import asyncio

import discord
from discord.ext import commands

from bot.utils.config import (
    DISCORD_TOKEN,
    DISCORD_GUILD_ID,
)


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=commands.DefaultHelpCommand(),
)


@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("Discord bot is online.")

    try:
        await bot.sync_commands(
            force=True,
            guild_ids=[DISCORD_GUILD_ID],
        )

        print(
            f"Slash commands synced to guild "
            f"{DISCORD_GUILD_ID}."
        )

    except Exception as exc:
        print(
            f"Slash command sync failed: "
            f"{type(exc).__name__}: {exc}"
        )

    print("Registered slash commands:")

    for command in bot.pending_application_commands:
        print(f"  /{command.name}")


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


def load_extensions():
    bot.load_extension("bot.commands.general")
    bot.load_extension("bot.commands.music")


async def main():
    load_extensions()

    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())