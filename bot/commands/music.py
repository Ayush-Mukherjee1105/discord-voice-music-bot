from discord.ext import commands

from bot.music.player import MusicPlayer
from bot.music.resolver import MusicResolver
from bot.voice.manager import join_voice_channel


class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.resolver = MusicResolver()
        self.player = MusicPlayer(bot)

    @commands.command()
    async def join(self, ctx):
        await join_voice_channel(ctx)

    @commands.command()
    async def leave(self, ctx):
        if not ctx.voice_client:
            await ctx.send(
                "I'm not connected to a voice channel."
            )
            return

        await self.player.leave(
            ctx.guild.id,
            ctx.voice_client,
        )

        await ctx.send("Left the voice channel.")

    @commands.command()
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            await ctx.send(
                "You need to be in a voice channel first."
            )
            return

        try:
            track = await self.resolver.resolve(
                query=query,
                requester_id=ctx.author.id,
                requester_name=ctx.author.display_name,
            )

        except Exception as exc:
            print(
                f"Resolver error: "
                f"{type(exc).__name__}: {exc}"
            )

            await ctx.send(
                "I couldn't find that song."
            )
            return

        voice_client = ctx.voice_client

        if voice_client is None:
            voice_client = await ctx.author.voice.channel.connect()

        elif voice_client.channel != ctx.author.voice.channel:
            await voice_client.move_to(
                ctx.author.voice.channel
            )

        self.player.cancel_idle_disconnect(
            ctx.guild.id
        )

        queue = self.player.get_queue(ctx.guild.id)
        queue.add(track)

        if (
            voice_client.is_playing()
            or voice_client.is_paused()
        ):
            position = len(queue)

            await ctx.send(
                f"Added **{track.title}** to the queue "
                f"(position {position})."
            )
            return

        await ctx.send(
            f"▶️ Playing **{track.title}**"
        )

        await self.player.play_next(
            ctx.guild,
            voice_client,
        )

    @commands.command()
    async def pause(self, ctx):
        if not ctx.voice_client:
            await ctx.send(
                "I'm not connected to a voice channel."
            )
            return

        if await self.player.pause(ctx.voice_client):
            await ctx.send("⏸️ Paused.")
        else:
            await ctx.send(
                "Nothing is currently playing."
            )

    @commands.command()
    async def resume(self, ctx):
        if not ctx.voice_client:
            await ctx.send(
                "I'm not connected to a voice channel."
            )
            return

        if await self.player.resume(ctx.voice_client):
            await ctx.send("▶️ Resumed.")
        else:
            await ctx.send(
                "Nothing is paused."
            )

    @commands.command()
    async def skip(self, ctx):
        if not ctx.voice_client:
            await ctx.send(
                "I'm not connected to a voice channel."
            )
            return

        if await self.player.skip(ctx.voice_client):
            await ctx.send("⏭️ Skipped.")
        else:
            await ctx.send(
                "Nothing is currently playing."
            )

    @commands.command()
    async def stop(self, ctx):
        if not ctx.voice_client:
            await ctx.send(
                "I'm not connected to a voice channel."
            )
            return

        await self.player.stop(
            ctx.guild.id,
            ctx.voice_client,
        )

        await ctx.send(
            "⏹️ Playback stopped and queue cleared."
        )

    @commands.command(name="queue")
    async def show_queue(self, ctx):
        queue = self.player.get_queue(ctx.guild.id)
        current = self.player.current.get(ctx.guild.id)

        lines = []

        if current:
            lines.append(
                f"▶️ **Now playing:** {current.title}"
            )

        items = queue.items()

        if items:
            lines.append("")
            lines.append("**Up next:**")

            for index, track in enumerate(items, start=1):
                lines.append(
                    f"`{index}.` {track.title} "
                    f"— {track.requester_name}"
                )

        if not lines:
            await ctx.send(
                "The queue is empty."
            )
            return

        await ctx.send(
            "\n".join(lines)
        )

    @commands.command()
    async def remove(self, ctx, index: int):
        track = self.player.remove(
            ctx.guild.id,
            index,
        )

        if track is None:
            await ctx.send(
                "Invalid queue position."
            )
            return

        await ctx.send(
            f"Removed **{track.title}** from the queue."
        )

    @commands.command()
    async def removeme(self, ctx):
        queue = self.player.get_queue(ctx.guild.id)

        track = queue.remove_user_last(
            ctx.author.id
        )

        if track is None:
            await ctx.send(
                "You don't have any songs in the queue."
            )
            return

        await ctx.send(
            f"Removed your last queued song: "
            f"**{track.title}**"
        )

    @commands.command()
    async def myqueue(self, ctx):
        queue = self.player.get_queue(ctx.guild.id)

        tracks = queue.user_items(
            ctx.author.id
        )

        if not tracks:
            await ctx.send(
                "You don't have any songs in the queue."
            )
            return

        lines = ["**Your queued songs:**"]

        for index, track in enumerate(tracks, start=1):
            lines.append(
                f"`{index}.` {track.title}"
            )

        await ctx.send(
            "\n".join(lines)
        )

    @commands.command()
    async def clear(self, ctx):
        self.player.clear_queue(
            ctx.guild.id
        )

        await ctx.send(
            "Queue cleared."
        )


def setup(bot):
    bot.add_cog(MusicCommands(bot))