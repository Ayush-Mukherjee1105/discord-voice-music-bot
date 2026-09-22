from collections import deque
import random

from bot.music.models import Track


class MusicQueue:
    def __init__(self):
        self._queue: deque[Track] = deque()

    def add(self, track: Track) -> None:
        self._queue.append(track)

    def add_front(self, track: Track) -> None:
        self._queue.appendleft(track)

    def get_next(self) -> Track | None:
        if not self._queue:
            return None

        return self._queue.popleft()

    def peek(self) -> Track | None:
        if not self._queue:
            return None

        return self._queue[0]

    def remove(self, index: int) -> Track | None:
        if index < 1 or index > len(self._queue):
            return None

        items = list(self._queue)
        track = items.pop(index - 1)

        self._queue = deque(items)

        return track

    def remove_user_last(self, user_id: int) -> Track | None:
        items = list(self._queue)

        for index in range(len(items) - 1, -1, -1):
            if items[index].requester_id == user_id:
                track = items.pop(index)
                self._queue = deque(items)
                return track

        return None

    def user_items(self, user_id: int) -> list[Track]:
        return [
            track
            for track in self._queue
            if track.requester_id == user_id
        ]

    def shuffle(self) -> None:
        items = list(self._queue)
        random.shuffle(items)
        self._queue = deque(items)

    def clear(self) -> None:
        self._queue.clear()

    def clear_user(self, user_id: int) -> int:
        original_length = len(self._queue)

        self._queue = deque(
            track
            for track in self._queue
            if track.requester_id != user_id
        )

        return original_length - len(self._queue)

    def __len__(self) -> int:
        return len(self._queue)

    def is_empty(self) -> bool:
        return not self._queue

    def items(self) -> list[Track]:
        return list(self._queue)