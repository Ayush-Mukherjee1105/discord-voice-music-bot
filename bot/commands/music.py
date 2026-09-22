import asyncio

import discord
from discord.ext import commands

from bot.music.player import MusicPlayer
from bot.music.resolver import MusicResolver
from bot.voice.manager import join_voice_channel


# ============================================================
# PLAYER UI
# ============================================================

class MusicPlayerView(discord.ui.View):

    def __init__(
        self,
        cog,
        guild_id: int,
    ):
        super().__init__(
            timeout=None
        )

        self.cog = cog
        self.guild_id = guild_id

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if interaction.guild is None:
            await interaction.response.send_message(
                "This control panel can only be used inside a server.",
                ephemeral=True,
            )
            return False

        if interaction.guild.id != self.guild_id:
            await interaction.response.send_message(
                "This player belongs to another server.",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(
        emoji="⏮️",
        style=discord.ButtonStyle.secondary,
        custom_id="music_previous",
    )
    async def previous(
        self,
        button,
        interaction: discord.Interaction,
    ):
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            await interaction.response.send_message(
                "I'm not connected to a voice channel.",
                ephemeral=True,
            )
            return

        success = await self.cog.player.previous(
            interaction.guild,
            voice_client,
        )

        if not success:
            await interaction.response.send_message(
                "There is no previous song.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        await self.cog.update_player_message(
            interaction.guild
        )

    @discord.ui.button(
        emoji="⏯️",
        style=discord.ButtonStyle.primary,
        custom_id="music_pause_resume",
    )
    async def pause_resume(
        self,
        button,
        interaction: discord.Interaction,
    ):
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            await interaction.response.send_message(
                "I'm not connected to a voice channel.",
                ephemeral=True,
            )
            return

        if voice_client.is_paused():
            await self.cog.player.resume(
                voice_client
            )

        elif voice_client.is_playing():
            await self.cog.player.pause(
                voice_client
            )

        else:
            await interaction.response.send_message(
                "Nothing is currently playing.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        await self.cog.update_player_message(
            interaction.guild
        )

    @discord.ui.button(
        emoji="⏭️",
        style=discord.ButtonStyle.secondary,
        custom_id="music_skip",
    )
    async def skip(
        self,
        button,
        interaction: discord.Interaction,
    ):
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            await interaction.response.send_message(
                "I'm not connected to a voice channel.",
                ephemeral=True,
            )
            return

        success = await self.cog.player.skip(
            voice_client
        )

        if not success:
            await interaction.response.send_message(
                "Nothing is currently playing.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        await self.cog.update_player_message(
            interaction.guild
        )

    @discord.ui.button(
        emoji="🔀",
        style=discord.ButtonStyle.secondary,
        custom_id="music_shuffle",
    )
    async def shuffle(
        self,
        button,
        interaction: discord.Interaction,
    ):
        self.cog.player.shuffle_queue(
            interaction.guild.id
        )

        await interaction.response.defer()

        await self.cog.update_player_message(
            interaction.guild
        )

    @discord.ui.button(
        emoji="🔁",
        style=discord.ButtonStyle.secondary,
        custom_id="music_loop",
    )
    async def loop(
        self,
        button,
        interaction: discord.Interaction,
    ):
        mode = self.cog.player.cycle_loop_mode(
            interaction.guild.id
        )

        await interaction.response.send_message(
            f"Loop mode: **{mode}**",
            ephemeral=True,
        )

        await self.cog.update_player_message(
            interaction.guild
        )

    @discord.ui.button(
        emoji="🛑",
        style=discord.ButtonStyle.danger,
        custom_id="music_stop",
    )
    async def stop(
        self,
        button,
        interaction: discord.Interaction,
    ):
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            await interaction.response.send_message(
                "I'm not connected to a voice channel.",
                ephemeral=True,
            )
            return

        await self.cog.player.stop(
            interaction.guild.id,
            voice_client,
        )

        await interaction.response.defer()

        await self.cog.update_player_message(
            interaction.guild
        )

    @discord.ui.button(
        label="Queue",
        emoji="📋",
        style=discord.ButtonStyle.secondary,
        custom_id="music_queue",
        row=2,
    )
    async def queue(
        self,
        button,
        interaction: discord.Interaction,
    ):
        queue_text = self.cog.build_queue_text(
            interaction.guild.id
        )

        await interaction.response.send_message(
            queue_text,
            ephemeral=True,
        )


# ============================================================
# AUTOCOMPLETE
# ============================================================

async def play_autocomplete(
    ctx: discord.AutocompleteContext,
):
    cog = ctx.cog

    if cog is None:
        return []

    results = await cog.resolver.autocomplete(
        ctx.value
    )

    return [
        discord.OptionChoice(
            name=title,
            value=url,
        )
        for title, url in results[:25]
    ]


async def remove_autocomplete(
    ctx: discord.AutocompleteContext,
):
    cog = ctx.cog

    if cog is None or ctx.guild is None:
        return []

    queue = cog.player.get_queue(
        ctx.guild.id
    )

    items = queue.items()

    return [
        discord.OptionChoice(
            name=f"{index}. {track.title}"[:100],
            value=str(index),
        )
        for index, track in enumerate(
            items,
            start=1,
        )
    ][:25]


# ============================================================
# MUSIC COMMANDS
# ============================================================

class MusicCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.resolver = MusicResolver()
        self.player = MusicPlayer(bot)

    # ========================================================
    # PREFIX COMMANDS
    # ========================================================

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

        await ctx.send(
            "Left the voice channel."
        )

    @commands.command()
    async def play(
        self,
        ctx,
        *,
        query: str,
    ):
        await self._play(
            ctx,
            query,
            ctx.send,
        )

    @commands.command()
    async def pause(self, ctx):
        if not ctx.voice_client:
            await ctx.send(
                "I'm not connected to a voice channel."
            )
            return

        if await self.player.pause(
            ctx.voice_client
        ):
            await ctx.send(
                "⏸️ Paused."
            )
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

        if await self.player.resume(
            ctx.voice_client
        ):
            await ctx.send(
                "▶️ Resumed."
            )
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

        if await self.player.skip(
            ctx.voice_client
        ):
            await ctx.send(
                "⏭️ Skipped."
            )
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

        await self.update_player_message(
            ctx.guild
        )

    @commands.command(name="queue")
    async def show_queue(self, ctx):
        await ctx.send(
            self.build_queue_text(
                ctx.guild.id
            )
        )

    @commands.command()
    async def remove(
        self,
        ctx,
        index: int,
    ):
        await self._remove(
            ctx.guild.id,
            index,
            ctx.send,
        )

    @commands.command()
    async def removeme(self, ctx):
        queue = self.player.get_queue(
            ctx.guild.id
        )

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

        await self.update_player_message(
            ctx.guild
        )

    @commands.command()
    async def myqueue(self, ctx):
        await self._myqueue(
            ctx.guild.id,
            ctx.author.id,
            ctx.send,
        )

    @commands.command()
    async def clear(self, ctx):
        self.player.clear_queue(
            ctx.guild.id
        )

        await ctx.send(
            "Queue cleared."
        )

        await self.update_player_message(
            ctx.guild
        )

    # ========================================================
    # SLASH COMMANDS
    # ========================================================

    @discord.slash_command(
        name="join",
        description="Join your current voice channel.",
    )
    async def slash_join(
        self,
        ctx: discord.ApplicationContext,
    ):
        await ctx.defer()

        if (
            not ctx.author.voice
            or not ctx.author.voice.channel
        ):
            await ctx.followup.send(
                "You need to be in a voice channel first."
            )
            return

        target_channel = (
            ctx.author.voice.channel
        )

        voice_client = ctx.voice_client

        try:
            if voice_client:

                if (
                    voice_client.channel
                    == target_channel
                ):
                    await ctx.followup.send(
                        f"I'm already in "
                        f"**{target_channel.name}**."
                    )
                    return

                await voice_client.move_to(
                    target_channel
                )

            else:
                voice_client = (
                    await target_channel.connect()
                )

            await ctx.guild.change_voice_state(
                channel=target_channel,
                self_deaf=True,
            )

            await ctx.followup.send(
                f"Joined **{target_channel.name}**."
            )

        except discord.ClientException as exc:
            await ctx.followup.send(
                f"Voice connection failed: "
                f"`{exc}`"
            )

        except asyncio.TimeoutError:
            await ctx.followup.send(
                "The voice connection timed out."
            )

        except Exception as exc:
            print(
                f"Slash join error: "
                f"{type(exc).__name__}: {exc}"
            )

            await ctx.followup.send(
                "I couldn't connect to the voice channel."
            )

    @discord.slash_command(
        name="leave",
        description="Leave the current voice channel.",
    )
    async def slash_leave(
        self,
        ctx: discord.ApplicationContext,
    ):
        if not ctx.voice_client:
            await ctx.respond(
                "I'm not connected to a voice channel."
            )
            return

        await self.player.leave(
            ctx.guild.id,
            ctx.voice_client,
        )

        await ctx.respond(
            "Left the voice channel."
        )

    # ========================================================
    # PLAY
    # ========================================================

    @discord.slash_command(
        name="play",
        description="Play a song or add it to the queue.",
    )
    @discord.option(
        "query",
        str,
        description="Search YouTube or enter a URL.",
        autocomplete=play_autocomplete,
    )
    async def slash_play(
        self,
        ctx: discord.ApplicationContext,
        query: str,
    ):
        await ctx.defer()

        await self._play(
            ctx,
            query,
            ctx.followup.send,
        )

    # ========================================================
    # PAUSE
    # ========================================================

    @discord.slash_command(
        name="pause",
        description="Pause the current song.",
    )
    async def slash_pause(
        self,
        ctx: discord.ApplicationContext,
    ):
        if not ctx.voice_client:
            await ctx.respond(
                "I'm not connected to a voice channel."
            )
            return

        if await self.player.pause(
            ctx.voice_client
        ):
            await ctx.respond(
                "⏸️ Paused."
            )
        else:
            await ctx.respond(
                "Nothing is currently playing."
            )

        await self.update_player_message(
            ctx.guild
        )

    # ========================================================
    # RESUME
    # ========================================================

    @discord.slash_command(
        name="resume",
        description="Resume the current song.",
    )
    async def slash_resume(
        self,
        ctx: discord.ApplicationContext,
    ):
        if not ctx.voice_client:
            await ctx.respond(
                "I'm not connected to a voice channel."
            )
            return

        if await self.player.resume(
            ctx.voice_client
        ):
            await ctx.respond(
                "▶️ Resumed."
            )
        else:
            await ctx.respond(
                "Nothing is paused."
            )

        await self.update_player_message(
            ctx.guild
        )

    # ========================================================
    # SKIP
    # ========================================================

    @discord.slash_command(
        name="skip",
        description="Skip the current song.",
    )
    async def slash_skip(
        self,
        ctx: discord.ApplicationContext,
    ):
        if not ctx.voice_client:
            await ctx.respond(
                "I'm not connected to a voice channel."
            )
            return

        if await self.player.skip(
            ctx.voice_client
        ):
            await ctx.respond(
                "⏭️ Skipped."
            )
        else:
            await ctx.respond(
                "Nothing is currently playing."
            )

        await self.update_player_message(
            ctx.guild
        )

    # ========================================================
    # PREVIOUS
    # ========================================================

    @discord.slash_command(
        name="previous",
        description="Play the previous song.",
    )
    async def slash_previous(
        self,
        ctx: discord.ApplicationContext,
    ):
        if not ctx.voice_client:
            await ctx.respond(
                "I'm not connected to a voice channel."
            )
            return

        if await self.player.previous(
            ctx.guild,
            ctx.voice_client,
        ):
            await ctx.respond(
                "⏮️ Previous song."
            )
        else:
            await ctx.respond(
                "There is no previous song."
            )

        await self.update_player_message(
            ctx.guild
        )

    # ========================================================
    # STOP
    # ========================================================

    @discord.slash_command(
        name="stop",
        description="Stop playback and clear the queue.",
    )
    async def slash_stop(
        self,
        ctx: discord.ApplicationContext,
    ):
        if not ctx.voice_client:
            await ctx.respond(
                "I'm not connected to a voice channel."
            )
            return

        await self.player.stop(
            ctx.guild.id,
            ctx.voice_client,
        )

        await ctx.respond(
            "⏹️ Playback stopped and queue cleared."
        )

        await self.update_player_message(
            ctx.guild
        )

    # ========================================================
    # NOW PLAYING
    # ========================================================

    @discord.slash_command(
        name="nowplaying",
        description="Show the current song.",
    )
    async def slash_nowplaying(
        self,
        ctx: discord.ApplicationContext,
    ):
        track = self.player.current.get(
            ctx.guild.id
        )

        if track is None:
            await ctx.respond(
                "Nothing is currently playing."
            )
            return

        await ctx.respond(
            f"🎵 **Now Playing**\n"
            f"**{track.title}**"
        )

    # ========================================================
    # QUEUE
    # ========================================================

    @discord.slash_command(
        name="queue",
        description="Show the current music queue.",
    )
    async def slash_queue(
        self,
        ctx: discord.ApplicationContext,
    ):
        await ctx.respond(
            self.build_queue_text(
                ctx.guild.id
            )
        )

    # ========================================================
    # REMOVE
    # ========================================================

    @discord.slash_command(
        name="remove",
        description="Remove a song from the queue.",
    )
    @discord.option(
        "index",
        int,
        description="Queue position",
        min_value=1,
        autocomplete=remove_autocomplete,
    )
    async def slash_remove(
        self,
        ctx: discord.ApplicationContext,
        index: int,
    ):
        await self._remove(
            ctx.guild.id,
            index,
            ctx.respond,
        )

        await self.update_player_message(
            ctx.guild
        )

    # ========================================================
    # REMOVE ME
    # ========================================================

    @discord.slash_command(
        name="removeme",
        description="Remove your last queued song.",
    )
    async def slash_removeme(
        self,
        ctx: discord.ApplicationContext,
    ):
        queue = self.player.get_queue(
            ctx.guild.id
        )

        track = queue.remove_user_last(
            ctx.author.id
        )

        if track is None:
            await ctx.respond(
                "You don't have any songs in the queue."
            )
            return

        await ctx.respond(
            f"Removed your last queued song: "
            f"**{track.title}**"
        )

        await self.update_player_message(
            ctx.guild
        )

    # ========================================================
    # MY QUEUE
    # ========================================================

    @discord.slash_command(
        name="myqueue",
        description="Show your queued songs.",
    )
    async def slash_myqueue(
        self,
        ctx: discord.ApplicationContext,
    ):
        await ctx.respond(
            self.build_myqueue_text(
                ctx.guild.id,
                ctx.author.id,
            )
        )

    # ========================================================
    # CLEAR
    # ========================================================

    @discord.slash_command(
        name="clear",
        description="Clear the music queue.",
    )
    async def slash_clear(
        self,
        ctx: discord.ApplicationContext,
    ):
        await ctx.respond(
            "Queue cleared."
        )

        self.player.clear_queue(
            ctx.guild.id
        )

        await self.update_player_message(
            ctx.guild
        )

    # ========================================================
    # SHUFFLE
    # ========================================================

    @discord.slash_command(
        name="shuffle",
        description="Shuffle the music queue.",
    )
    async def slash_shuffle(
        self,
        ctx: discord.ApplicationContext,
    ):
        self.player.shuffle_queue(
            ctx.guild.id
        )

        await ctx.respond(
            "🔀 Queue shuffled."
        )

        await self.update_player_message(
            ctx.guild
        )

    # ========================================================
    # LOOP
    # ========================================================

    @discord.slash_command(
        name="loop",
        description="Cycle through loop modes.",
    )
    async def slash_loop(
        self,
        ctx: discord.ApplicationContext,
    ):
        mode = self.player.cycle_loop_mode(
            ctx.guild.id
        )

        await ctx.respond(
            f"🔁 Loop mode: **{mode}**"
        )

        await self.update_player_message(
            ctx.guild
        )

    # ========================================================
    # SHARED PLAY
    # ========================================================

    async def _play(
        self,
        ctx,
        query: str,
        respond,
    ):
        if not ctx.author.voice:
            await respond(
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

            await respond(
                "I couldn't find that song."
            )
            return

        voice_client = ctx.voice_client

        if voice_client is None:
            voice_client = (
                await ctx.author.voice.channel.connect()
            )

            await ctx.guild.change_voice_state(
                channel=ctx.author.voice.channel,
                self_deaf=True,
            )

        elif (
            voice_client.channel
            != ctx.author.voice.channel
        ):
            await voice_client.move_to(
                ctx.author.voice.channel
            )

            await ctx.guild.change_voice_state(
                channel=ctx.author.voice.channel,
                self_deaf=True,
            )

        self.player.cancel_idle_disconnect(
            ctx.guild.id
        )

        queue = self.player.get_queue(
            ctx.guild.id
        )

        queue.add(track)

        if (
            voice_client.is_playing()
            or voice_client.is_paused()
        ):
            position = len(queue)

            await respond(
                f"✅ Added **{track.title}** "
                f"to the queue "
                f"(position {position})."
            )

        else:
            await respond(
                f"▶️ Playing **{track.title}**"
            )

            await self.player.play_next(
                ctx.guild,
                voice_client,
            )

        await self.update_player_message(
            ctx.guild,
            channel=ctx.channel,
        )

    # ========================================================
    # PLAYER MESSAGE
    # ========================================================

    def build_player_embed(
        self,
        guild_id: int,
    ) -> discord.Embed:

        current = self.player.current.get(
            guild_id
        )

        queue = self.player.get_queue(
            guild_id
        )

        loop_mode = self.player.get_loop_mode(
            guild_id
        )

        if current is None:
            embed = discord.Embed(
                title="🎵 Music Player",
                description=(
                    "Nothing is currently playing.\n\n"
                    "Use `/play` to start listening."
                ),
            )

        else:
            duration = self.format_duration(
                current.duration
            )

            embed = discord.Embed(
                title="🎵 Now Playing",
                description=(
                    f"**{current.title}**\n\n"
                    f"👤 Requested by "
                    f"**{current.requester_name}**\n"
                    f"⏱️ {duration}"
                ),
            )

            if current.webpage_url:
                embed.url = current.webpage_url

        embed.add_field(
            name="Queue",
            value=str(len(queue)),
            inline=True,
        )

        embed.add_field(
            name="Loop",
            value=loop_mode,
            inline=True,
        )

        embed.set_footer(
            text="Use the buttons below to control playback."
        )

        return embed

    async def update_player_message(
        self,
        guild: discord.Guild,
        channel=None,
    ):
        guild_id = guild.id

        stored = self.player.get_player_message(
            guild_id
        )

        target_channel = channel

        if target_channel is None and stored:
            channel_id, _ = stored

            target_channel = guild.get_channel(
                channel_id
            )

        if target_channel is None:
            return

        message = None

        if stored:
            _, message_id = stored

            try:
                message = await target_channel.fetch_message(
                    message_id
                )

            except (
                discord.NotFound,
                discord.HTTPException,
            ):
                message = None

        view = MusicPlayerView(
            self,
            guild_id,
        )

        embed = self.build_player_embed(
            guild_id
        )

        if message is None:
            try:
                message = await target_channel.send(
                    embed=embed,
                    view=view,
                )

            except discord.HTTPException as exc:
                print(
                    f"Player message error: "
                    f"{type(exc).__name__}: {exc}"
                )
                return

            self.player.set_player_message(
                guild_id,
                target_channel.id,
                message.id,
            )

        else:
            try:
                await message.edit(
                    embed=embed,
                    view=view,
                )

            except discord.NotFound:
                self.player.clear_player_message(
                    guild_id
                )

            except discord.HTTPException as exc:
                print(
                    f"Player update error: "
                    f"{type(exc).__name__}: {exc}"
                )

    # ========================================================
    # QUEUE DISPLAY
    # ========================================================

    def build_queue_text(
        self,
        guild_id: int,
    ) -> str:

        queue = self.player.get_queue(
            guild_id
        )

        current = self.player.current.get(
            guild_id
        )

        lines = []

        if current:
            lines.append(
                f"▶️ **Now Playing:** "
                f"{current.title}"
            )

        items = queue.items()

        if items:
            lines.append("")
            lines.append("**Up Next:**")

            for index, track in enumerate(
                items,
                start=1,
            ):
                lines.append(
                    f"`{index}.` "
                    f"**{track.title}** "
                    f"— {track.requester_name}"
                )

        if not lines:
            return "🎵 The queue is empty."

        return "\n".join(lines)

    def build_myqueue_text(
        self,
        guild_id: int,
        user_id: int,
    ) -> str:

        queue = self.player.get_queue(
            guild_id
        )

        tracks = queue.user_items(
            user_id
        )

        if not tracks:
            return (
                "You don't have any songs "
                "in the queue."
            )

        lines = [
            "**Your queued songs:**"
        ]

        for index, track in enumerate(
            tracks,
            start=1,
        ):
            lines.append(
                f"`{index}.` {track.title}"
            )

        return "\n".join(lines)

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def format_duration(
        seconds: int | None,
    ) -> str:

        if seconds is None:
            return "Unknown duration"

        minutes, seconds = divmod(
            int(seconds),
            60,
        )

        hours, minutes = divmod(
            minutes,
            60,
        )

        if hours:
            return (
                f"{hours}:{minutes:02d}:"
                f"{seconds:02d}"
            )

        return (
            f"{minutes}:{seconds:02d}"
        )

    async def _remove(
        self,
        guild_id: int,
        index: int,
        respond,
    ):
        track = self.player.remove(
            guild_id,
            index,
        )

        if track is None:
            await respond(
                "Invalid queue position."
            )
            return

        await respond(
            f"Removed **{track.title}** "
            f"from the queue."
        )

    async def _myqueue(
        self,
        guild_id: int,
        user_id: int,
        respond,
    ):
        await respond(
            self.build_myqueue_text(
                guild_id,
                user_id,
            )
        )


def setup(bot):
    bot.add_cog(
        MusicCommands(bot)
    )