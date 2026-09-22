from __future__ import annotations

import asyncio
from functools import partial

import yt_dlp

from bot.music.models import Track


YTDL_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "extract_flat": False,
    "skip_download": True,
    "format": "bestaudio/best",
}


class MusicResolver:
    def __init__(self):
        self._youtube = yt_dlp.YoutubeDL(YTDL_OPTIONS)

    async def resolve(
        self,
        query: str,
        requester_id: int,
        requester_name: str,
    ) -> Track:

        loop = asyncio.get_running_loop()

        extract = partial(
            self._extract,
            query,
        )

        info = await loop.run_in_executor(None, extract)

        if not info:
            raise RuntimeError("No results were found.")

        return Track(
            title=info.get("title", "Unknown title"),
            url=info["webpage_url"],
            webpage_url=info.get("webpage_url", info["url"]),
            duration=info.get("duration"),
            requester_id=requester_id,
            requester_name=requester_name,
        )

    def _extract(self, query: str) -> dict:
        if query.startswith(("http://", "https://")):
            search_query = query
        else:
            search_query = f"ytsearch1:{query}"

        info = self._youtube.extract_info(
            search_query,
            download=False,
        )

        if "entries" in info:
            entries = info.get("entries") or []

            if not entries:
                raise RuntimeError(
                    "No YouTube results were found."
                )

            return entries[0]

        return info