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

AUTOCOMPLETE_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "extract_flat": True,
    "skip_download": True,
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

        info = await loop.run_in_executor(
            None,
            extract,
        )

        if not info:
            raise RuntimeError(
                "No results were found."
            )

        return Track(
            title=info.get(
                "title",
                "Unknown title",
            ),
            url=info["webpage_url"],
            webpage_url=info.get(
                "webpage_url",
                info["url"],
            ),
            duration=info.get("duration"),
            requester_id=requester_id,
            requester_name=requester_name,
        )

    async def autocomplete(
        self,
        query: str,
    ) -> list[tuple[str, str]]:
        if not query or len(query.strip()) < 2:
            return []

        loop = asyncio.get_running_loop()

        search = partial(
            self._autocomplete_search,
            query.strip(),
        )

        try:
            return await loop.run_in_executor(
                None,
                search,
            )

        except Exception as exc:
            print(
                f"Autocomplete error: "
                f"{type(exc).__name__}: {exc}"
            )

            return []

    def _extract(
        self,
        query: str,
    ) -> dict:
        if query.startswith(
            ("http://", "https://")
        ):
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

    @staticmethod
    def _autocomplete_search(
        query: str,
    ) -> list[tuple[str, str]]:

        with yt_dlp.YoutubeDL(
            AUTOCOMPLETE_OPTIONS
        ) as ydl:

            info = ydl.extract_info(
                f"ytsearch5:{query}",
                download=False,
            )

        entries = info.get("entries") or []

        results = []

        for entry in entries:
            title = entry.get("title")
            webpage_url = (
                entry.get("webpage_url")
                or entry.get("url")
            )

            if not title or not webpage_url:
                continue

            results.append(
                (
                    title[:100],
                    webpage_url,
                )
            )

        return results