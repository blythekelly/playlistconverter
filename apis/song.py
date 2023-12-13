from dataclasses import dataclass
import datetime
import json


@dataclass
class Song:
    title: str
    artists: list[str]
    album: str | None = None
    released: datetime.date | None = None

    def serialize(self) -> tuple:
        return (
            self.title,
            self.artists,
            self.album,
            self.released.isoformat() if self.released else None
        )

    @classmethod
    def deserialize(cls, data: tuple) -> 'Song':
        title, artists, album, released = data

        if released:
            released = datetime.datetime.fromisoformat(released)

        return Song(title, artists, album, released)

    def to_json(self) -> str:
        return json.dumps({
            'title': self.title,
            'artists': self.artists,
            'album': self.album,
            'released': self.released.isoformat() if self.released else None
        })

    @classmethod
    def from_json(cls, song: str) -> 'Song':
        data = json.loads(song)

        title = data['title']
        artists = data['artists']
        album = data['album']
        if raw_date := data['released']:
            released = datetime.datetime.fromisoformat(raw_date)
        else:
            released = None

        return Song(title, artists, album, released)
