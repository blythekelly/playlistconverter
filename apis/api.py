from abc import ABC, abstractmethod
from song import Song


ID = str


class API(ABC):
    @abstractmethod
    def search(self, song: Song) -> ID | None:
        pass

    @abstractmethod
    def get_playlist(self, id: ID) -> list[Song]:
        pass

    @abstractmethod
    def create_playlist(self, name: str, songs: list[Song]):
        pass
