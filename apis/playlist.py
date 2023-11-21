from dataclasses import dataclass


@dataclass
class Playlist:
    title: str
    id: str
    image: str | None = None
