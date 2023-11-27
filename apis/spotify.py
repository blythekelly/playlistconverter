import concurrent.futures
from dataclasses import dataclass
import datetime
import itertools
import json
import time

import requests

from .api import API, ID
from .song import Song
from .playlist import Playlist


def get_client_id() -> str:
    return '2f94b612382c4c0a82feb3c7289b3043'


@dataclass
class Token:
    access_code: str
    refresh_code: str
    expiry: float

    def validate(self):
        # Don't refresh the token if it will be valid for at least a
        # minute.
        if time.time() + 60 < self.expiry:
            return

        self.refresh()

    def refresh(self):
        URL = 'https://accounts.spotify.com/api/token'
        body = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_code,
            'client_id': get_client_id()
        }

        response = requests.post(URL, body)

        if (code := response.status_code) != 200:
            raise RuntimeError(f"couldn't refresh token (code {code})")

        result = json.loads(response.content)
        self.access_code = result['access_token']
        self.refresh_code = result['refresh_token']
        self.expiry = time.time() + result['expires_in']

class SpotifyAPI(API):
    def __init__(self, authorization_code: str, verifier: str, redirect: str):
        response = requests.post(
            'https://accounts.spotify.com/api/token',
            data={
                'code': authorization_code,
                'code_verifier': verifier,
                'client_id': get_client_id(),
                'grant_type': 'authorization_code',
                'redirect_uri': redirect
            }
        )

        if (code := response.status_code) != 200:
            raise RuntimeError(f'authentication failed (code {code})')

        result = json.loads(response.content)

        access = result['access_token']
        refresh = result['refresh_token']
        expiry = time.time() + result['expires_in']

        self.token = Token(access, refresh, expiry)

    @staticmethod
    def authorize(method):
        def wrapper(self: 'SpotifyAPI', *args):
            self.token.validate()

            return method(self, *args)

        return wrapper

    @authorize
    def search(self, song: Song) -> ID | None:
        URL = 'https://api.spotify.com/v1/search'

        headers = {'Authorization': f'Bearer {self.token.access_code}'}
        params = {
            'q': ' '.join((song.title, *song.artists)),
            'type': 'track'
        }

        response = requests.get(URL, params, headers=headers)
        result = json.loads(response.content)

        if (code := response.status_code) != 200:
            raise RuntimeError(f'API returned status code {code}')

        # TODO: Return the most relevant song instead of the first.
        return result['tracks']['items'][0]['id']

    @authorize
    def get_playlist(self, id: str) -> list[Song]:
        songs = []

        URL = f'https://api.spotify.com/v1/playlists/{id}/tracks'
        headers = {'Authorization': f'Bearer {self.token.access_code}'}
        params = {
            'fields': 'items(track(name,artists(name),album(name,release_date,release_date_precision))),next'
        }

        def to_song(item) -> Song:
            track = item['track']

            title = track['name']
            artists = [artist['name'] for artist in track['artists']]
            album = track['album']['name']

            date_string = track['album']['release_date']
            precision = track['album']['release_date_precision']
            date_formats = {
                'year': '%Y',
                'month': '%Y-%m',
                'day': '%Y-%m-%d'
            }
            date_format = date_formats[precision]

            parse_date = datetime.datetime.strptime
            date = parse_date(date_string, date_format).date()

            return Song(title, artists, album, date)

        while URL:
            response = requests.get(URL, params, headers=headers)
            result = json.loads(response.content)

            if (code := response.status_code) != 200:
                raise RuntimeError(f'{code}: {result['error']['message']}')

            songs.extend(map(to_song, result['items']))

            URL = result['next']

        return songs

    @authorize
    def get_user_playlists(self) -> list[Playlist]:
        playlists = []

        URL = 'https://api.spotify.com/v1/me/playlists'
        headers = {'Authorization': f'Bearer {self.token.access_code}'}

        while URL:
            response = requests.get(URL, headers=headers)
            result = json.loads(response.content)

            if (code := response.status_code) != 200:
                raise RuntimeError("couldn't load playlists\n"
                                   f'{code}: {result['error']['message']})')

            def to_playlist(item) -> Playlist:
                title = item['name']
                id = item['id']

                images = item['images']
                image = images[0]['url'] if images else None

                return Playlist(title, id, image)

            playlists.extend(map(to_playlist, result['items']))

            URL = result['next']

        return playlists

    @authorize
    def get_user_id(self) -> ID:
        URL = 'https://api.spotify.com/v1/me'
        headers = {'Authorization': f'Bearer {self.token.access_code}'}

        response = requests.get(URL, headers=headers)
        result = json.loads(response.content)

        if (code := response.status_code) != 200:
            raise RuntimeError(f'{code}: {result['error']['message']}')

        return result['id']

    @authorize
    def create_playlist(self, name: str, songs: list[Song]):
        # Search for the requested songs.
        with concurrent.futures.ThreadPoolExecutor() as executor:
            song_ids = filter(lambda id: id is not None,
                              executor.map(self.search, songs))

        # Create the playlist.
        response = requests.post(
            f'https://api.spotify.com/v1/users/{self.get_user_id()}/playlists',
            json={
                'name': name,
                'public': False,
                'description': 'generated by Playlist Converter'
            },
            headers={'Authorization': f'Bearer {self.token.access_code}'}
        )

        result = json.loads(response.content)

        if (code := response.status_code) != 201:
            raise RuntimeError("couldn't create playlist\n"
                               f'{code}: {result['error']['message']}')

        playlist_id = result['id']

        # The Spotify API only allows 100 songs to be added at a time,
        # so we divide them into batches.
        for batch in itertools.batched(song_ids, 100):
            URL = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
            body = {'uris': [f'spotify:track:{id}' for id in batch]}
            headers = {'Authorization': f'Bearer {self.token.access_code}'}

            response = requests.post(URL, json=body, headers=headers)
            if (code := response.status_code) != 201:
                result = json.loads(response.content)
                raise RuntimeError(f'{code}: {result['error']['message']}')
