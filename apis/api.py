from abc import ABC, abstractmethod

from .song import Song
from .playlist import Playlist


type ID = str


class API(ABC):
    @abstractmethod
    def search(self, song: Song) -> ID | None:
        """Find a song.

        args:
            - `song`: song to search for

        returns:
            - unique, platform-specific song identifier
            - `None` (if the song can't be found)
        """

    @abstractmethod
    def get_playlist(self, id: ID) -> list[Song]:
        """Get a playlist's songs.

        args:
            - `id`: unique, platform-specific playlist identifier

        returns:
            - list of songs found in the requested playlist
        """

    @abstractmethod
    def get_user_playlists(self) -> list[Playlist]:
        """Get the user's playlists.

        returns:
            - list of playlists
        """

    @abstractmethod
    def create_playlist(self, name: str, songs: list[Song], public: bool = False):
        """Create a playlist.

        args:
            - `name`: name of the created playlist
            - `songs`: songs to add to the playlist
            - `public`: whether the playlist should be publicly visible
        """
