from dataclasses import dataclass
import datetime


@dataclass
class Song:
    title: str
    artists: list[str]
    album: str | None = None
    released: datetime.date | None = None
