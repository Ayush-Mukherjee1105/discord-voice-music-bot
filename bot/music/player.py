from __future__ import annotations

import asyncio
from collections import deque

import discord
import yt_dlp

from bot.music.models import Track
from bot.music.queue import MusicQueue


YTDL_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "format": "bestaudio/best",
}

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": "-vn",
}

IDLE_DISCONNECT_DELAY = 300


class MusicPlayer:
    def __init__(self, bot: discord.Bot):
        self.bot = bot

        self.queues: dict[int, MusicQueue] = {}
        self.current: dict[int, Track] = {}

        self.history: dict[int, deque[Track]] = {}

        self.loop_mode: dict[int, str] = {}

        self._locks: dict[int, asyncio.Lock] = {}
        self._idle_tasks: dict[int, asyncio.Task] = {}

        self.player_messages: dict[int, int] = {}
        self.player_channels: dict[int, int] = {}

        self.started_at: dict[int, float] = {}

    # =========================
    # QUEUE
    # =========================

    def get_queue(self, guild_id: int) -> MusicQueue:
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()

        return self.queues[guild_id]

    def get_history(self, guild_id: int) -> deque[Track]:
        if guild_id not in self.history:
            self.history[guild_id] = deque(maxlen=50)

        return self.history[guild_id]

    # =========================
    # LOCK
    # =========================

    def _get_lock(self, guild_id: int) -> asyncio.Lock:
        if guild_id not in self._locks:
            self._locks[guild_id] = asyncio.Lock()

        return self._locks[guild_id]

    # =========================
    # PLAYER MESSAGE
    # =========================

    def set_player_message(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
    ) -> None:
        self.player_channels[guild_id] = channel_id
        self.player_messages[guild_id] = message_id

    def get_player_message(
        self,
        guild_id: int,
    ) -> tuple[int, int] | None:
        channel_id = self.player_channels.get(guild_id)
        message_id = self.player_messages.get(guild_id)

        if channel_id is None or message_id is None:
            return None

        return channel_id, message_id

    def clear_player_message(
        self,
        guild_id: int,
    ) -> None:
        self.player_channels.pop(guild_id, None)
        self.player_messages.pop(guild_id, None)

    # =========================
    # LOOP
    # =========================

    def get_loop_mode(self, guild_id: int) -> str:
        return self.loop_mode.get(guild_id, "off")

    def cycle_loop_mode(self, guild_id: int) -> str:
        current = self.get_loop_mode(guild_id)

        if current == "off":
            new_mode = "one"

        elif current == "one":
            new_mode = "all"

        else:
            new_mode = "off"

        self.loop_mode[guild_id] = new_mode

        return new_mode

    # =========================
    # IDLE DISCONNECT
    # =========================

    def cancel_idle_disconnect(self, guild_id: int) -> None:
        task = self._idle_tasks.pop(guild_id, None)

        if task and not task.done():
            task.cancel()

    def schedule_idle_disconnect(
        self,
        guild: discord.Guild,
        voice_client: discord.VoiceClient,
    ) -> None:
        self.cancel_idle_disconnect(guild.id)

        self._idle_tasks[guild.id] = asyncio.create_task(
            self._idle_disconnect(
                guild,
                voice_client,
            )
        )

    async def _idle_disconnect(
        self,
        guild: discord.Guild,
        voice_client: discord.VoiceClient,
    ) -> None:
        try:
            await asyncio.sleep(
                IDLE_DISCONNECT_DELAY
            )

            queue = self.get_queue(guild.id)

            if (
                queue.is_empty()
                and not voice_client.is_playing()
                and not voice_client.is_paused()
                and voice_client.is_connected()
            ):
                await voice_client.disconnect()

                self.current.pop(
                    guild.id,
                    None,
                )

        except asyncio.CancelledError:
            pass

        finally:
            self._idle_tasks.pop(
                guild.id,
                None,
            )

    # =========================
    # PLAYBACK
    # =========================

    async def play_next(
        self,
        guild: discord.Guild,
        voice_client: discord.VoiceClient,
    ) -> None:

        guild_id = guild.id

        self.cancel_idle_disconnect(
            guild_id
        )

        async with self._get_lock(guild_id):

            queue = self.get_queue(
                guild_id
            )

            current = self.current.get(
                guild_id
            )

            loop_mode = self.get_loop_mode(
                guild_id
            )

            # LOOP ONE
            if (
                loop_mode == "one"
                and current is not None
            ):
                track = current

            else:
                # Save finished track to history.
                if current is not None:
                    history = self.get_history(
                        guild_id
                    )

                    if (
                        not history
                        or history[-1] != current
                    ):
                        history.append(current)

                track = queue.get_next()

                if track is None:
                    self.current.pop(
                        guild_id,
                        None
                    )

                    if voice_client.is_connected():
                        self.schedule_idle_disconnect(
                            guild,
                            voice_client,
                        )

                    return

                self.current[guild_id] = track

            try:
                stream_url = await self._get_stream_url(
                    track.webpage_url
                )

                source = discord.FFmpegPCMAudio(
                    stream_url,
                    **FFMPEG_OPTIONS,
                )

                self.started_at[guild_id] = (
                    asyncio.get_running_loop().time()
                )

                def after_play(error):
                    if error:
                        print(
                            f"Playback error in "
                            f"{guild.name}: "
                            f"{type(error).__name__}: "
                            f"{error}"
                        )

                    asyncio.run_coroutine_threadsafe(
                        self.play_next(
                            guild,
                            voice_client,
                        ),
                        self.bot.loop,
                    )

                voice_client.play(
                    source,
                    after=after_play,
                )

            except Exception as exc:
                self.current.pop(
                    guild_id,
                    None,
                )

                print(
                    f"Unable to play "
                    f"'{track.title}': "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                await self.play_next(
                    guild,
                    voice_client,
                )

    async def _get_stream_url(
        self,
        url: str,
    ) -> str:

        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            None,
            self._extract_stream_url,
            url,
        )

    @staticmethod
    def _extract_stream_url(
        url: str,
    ) -> str:

        with yt_dlp.YoutubeDL(
            YTDL_OPTIONS
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=False,
            )

            if not info:
                raise RuntimeError(
                    "Unable to resolve audio."
                )

            return info["url"]

    # =========================
    # PAUSE / RESUME
    # =========================

    async def pause(
        self,
        voice_client: discord.VoiceClient,
    ) -> bool:

        if not voice_client.is_playing():
            return False

        voice_client.pause()

        return True

    async def resume(
        self,
        voice_client: discord.VoiceClient,
    ) -> bool:

        if not voice_client.is_paused():
            return False

        voice_client.resume()

        return True

    # =========================
    # SKIP
    # =========================

    async def skip(
        self,
        voice_client: discord.VoiceClient,
    ) -> bool:

        if (
            not voice_client.is_playing()
            and not voice_client.is_paused()
        ):
            return False

        voice_client.stop()

        return True

    # =========================
    # PREVIOUS
    # =========================

    async def previous(
        self,
        guild: discord.Guild,
        voice_client: discord.VoiceClient,
    ) -> bool:

        guild_id = guild.id

        history = self.get_history(
            guild_id
        )

        if not history:
            return False

        current = self.current.get(
            guild_id
        )

        if current is not None:
            self.get_queue(
                guild_id
            ).add_front(current)

        previous_track = history.pop()

        self.current.pop(
            guild_id,
            None,
        )

        if (
            voice_client.is_playing()
            or voice_client.is_paused()
        ):
            voice_client.stop()

        self.get_queue(
            guild_id
        ).add_front(
            previous_track
        )

        return True

    # =========================
    # STOP
    # =========================

    async def stop(
        self,
        guild_id: int,
        voice_client: discord.VoiceClient,
    ) -> None:

        self.cancel_idle_disconnect(
            guild_id
        )

        self.get_queue(
            guild_id
        ).clear()

        self.current.pop(
            guild_id,
            None,
        )

        self.get_history(
            guild_id
        ).clear()

        self.loop_mode[
            guild_id
        ] = "off"

        self.started_at.pop(
            guild_id,
            None,
        )

        if (
            voice_client.is_playing()
            or voice_client.is_paused()
        ):
            voice_client.stop()

    # =========================
    # LEAVE
    # =========================

    async def leave(
        self,
        guild_id: int,
        voice_client: discord.VoiceClient,
    ) -> None:

        self.cancel_idle_disconnect(
            guild_id
        )

        self.get_queue(
            guild_id
        ).clear()

        self.current.pop(
            guild_id,
            None,
        )

        self.get_history(
            guild_id
        ).clear()

        self.loop_mode[
            guild_id
        ] = "off"

        self.started_at.pop(
            guild_id,
            None,
        )

        if voice_client.is_connected():
            await voice_client.disconnect()

    # =========================
    # QUEUE MANAGEMENT
    # =========================

    def remove(
        self,
        guild_id: int,
        index: int,
    ) -> Track | None:

        return self.get_queue(
            guild_id
        ).remove(index)

    def clear_queue(
        self,
        guild_id: int,
    ) -> None:

        self.get_queue(
            guild_id
        ).clear()

    def shuffle_queue(
        self,
        guild_id: int,
    ) -> None:

        self.get_queue(
            guild_id
        ).shuffle()