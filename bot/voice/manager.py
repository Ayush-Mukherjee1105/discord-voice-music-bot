import asyncio

import discord


async def join_voice_channel(ctx):
    """Join or move to the voice channel of the command author."""

    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send(
            "You need to be in a voice channel first."
        )
        return

    target_channel = ctx.author.voice.channel
    voice_client = ctx.voice_client

    try:
        if voice_client:
            if voice_client.channel == target_channel:
                await ctx.send(
                    f"I'm already in **{target_channel.name}**."
                )
                return

            await voice_client.move_to(target_channel)

            await ctx.guild.change_voice_state(
                channel=target_channel,
                self_deaf=True,
            )

            await ctx.send(
                f"Moved to **{target_channel.name}**."
            )
            return

        voice_client = await target_channel.connect()

        await ctx.guild.change_voice_state(
            channel=target_channel,
            self_deaf=True,
        )

        if hasattr(voice_client, "is_dave_connection"):
            if voice_client.is_dave_connection():
                await ctx.send(
                    f"Joined **{target_channel.name}**."
                )
            else:
                await ctx.send(
                    f"Joined **{target_channel.name}**, "
                    "but the DAVE voice connection was not established."
                )
        else:
            await ctx.send(
                f"Joined **{target_channel.name}**."
            )

    except discord.ClientException as exc:
        await ctx.send(
            f"Voice connection failed: `{exc}`"
        )

    except asyncio.TimeoutError:
        await ctx.send(
            "The voice connection timed out."
        )

    except Exception as exc:
        print(
            f"Voice connection error: "
            f"{type(exc).__name__}: {exc}"
        )

        await ctx.send(
            "I couldn't connect to the voice channel."
        )