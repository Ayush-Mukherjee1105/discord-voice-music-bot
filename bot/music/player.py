from __future__ import annotations

import asyncio

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
        self._locks: dict[int, asyncio.Lock] = {}
        self._idle_tasks: dict[int, asyncio.Task] = {}

    def get_queue(self, guild_id: int) -> MusicQueue:
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()

        return self.queues[guild_id]

    def _get_lock(self, guild_id: int) -> asyncio.Lock:
        if guild_id not in self._locks:
            self._locks[guild_id] = asyncio.Lock()

        return self._locks[guild_id]

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
            self._idle_disconnect(guild, voice_client)
        )

    async def _idle_disconnect(
        self,
        guild: discord.Guild,
        voice_client: discord.VoiceClient,
    ) -> None:
        try:
            await asyncio.sleep(IDLE_DISCONNECT_DELAY)

            queue = self.get_queue(guild.id)

            if (
                queue.is_empty()
                and not voice_client.is_playing()
                and not voice_client.is_paused()
                and voice_client.is_connected()
            ):
                await voice_client.disconnect()

                self.current.pop(guild.id, None)

        except asyncio.CancelledError:
            pass

        finally:
            self._idle_tasks.pop(guild.id, None)

    async def play_next(
        self,
        guild: discord.Guild,
        voice_client: discord.VoiceClient,
    ) -> None:

        guild_id = guild.id

        self.cancel_idle_disconnect(guild_id)

        async with self._get_lock(guild_id):
            queue = self.get_queue(guild_id)

            track = queue.get_next()

            if track is None:
                self.current.pop(guild_id, None)

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

                def after_play(error):
                    if error:
                        print(
                            f"Playback error in {guild.name}: "
                            f"{type(error).__name__}: {error}"
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
                self.current.pop(guild_id, None)

                print(
                    f"Unable to play '{track.title}': "
                    f"{type(exc).__name__}: {exc}"
                )

                await self.play_next(
                    guild,
                    voice_client,
                )

    async def _get_stream_url(self, url: str) -> str:
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            None,
            self._extract_stream_url,
            url,
        )

    @staticmethod
    def _extract_stream_url(url: str) -> str:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(
                url,
                download=False,
            )

            if not info:
                raise RuntimeError(
                    "Unable to resolve audio."
                )

            return info["url"]

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

    async def stop(
        self,
        guild_id: int,
        voice_client: discord.VoiceClient,
    ) -> None:

        self.cancel_idle_disconnect(guild_id)

        self.get_queue(guild_id).clear()
        self.current.pop(guild_id, None)

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()

    async def skip(
        self,
        voice_client: discord.VoiceClient,
    ) -> bool:

        if not voice_client.is_playing() and not voice_client.is_paused():
            return False

        voice_client.stop()
        return True

    async def leave(
        self,
        guild_id: int,
        voice_client: discord.VoiceClient,
    ) -> None:

        self.cancel_idle_disconnect(guild_id)

        self.get_queue(guild_id).clear()
        self.current.pop(guild_id, None)

        if voice_client.is_connected():
            await voice_client.disconnect()

    def remove(
        self,
        guild_id: int,
        index: int,
    ) -> Track | None:

        return self.get_queue(guild_id).remove(index)

    def clear_queue(
        self,
        guild_id: int,
    ) -> None:

        self.get_queue(guild_id).clear()