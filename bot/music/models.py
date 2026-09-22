from dataclasses import dataclass


@dataclass
class Track:
    title: str
    url: str
    webpage_url: str
    duration: int | None
    requester_id: int
    requester_name: str