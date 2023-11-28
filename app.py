from base64 import urlsafe_b64encode
from hashlib import sha256
import secrets
from urllib.parse import quote, unquote, urlencode
from uuid import uuid4

from flask import Flask, make_response, redirect, render_template, request

from apis import API, SpotifyAPI
from apis.song import Song


app = Flask(__name__)

services = ['spotify']

apis: dict[str, dict[str, API | None]] = {}

# temporary workaround to share state between functions for
# authentication
auth = {service: {} for service in services}


def get_spotify_client_id() -> str:
    # TODO: Use Azure Key Vault.
    return '2f94b612382c4c0a82feb3c7289b3043'


def authenticate(service: str, redirect: str):
    authenticators = {
        'spotify': authenticate_spotify,
    }

    authenticator = authenticators[service]
    return authenticator(redirect)


def authenticate_spotify(dest: str):
    verifier = secrets.token_urlsafe(100)[:64].encode()
    challenge = urlsafe_b64encode(sha256(verifier).digest()).decode().rstrip('=')

    redirect_uri = f'https://playlistconverter.azurewebsites.net/spotify-auth?dest={quote(dest, safe='')}'

    params = urlencode({
        'client_id': auth['spotify']['id'],
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'code_challenge': challenge,
        'code_challenge_method': 'S256',
        'scope': 'playlist-modify-public playlist-modify-private playlist-read-private',
        # TODO: Add 'state': <value>,
    })

    URL = 'https://accounts.spotify.com/authorize'
    response = make_response(redirect(URL + '?' + params))
    response.set_cookie('spotify-verifier', verifier.decode())
    response.set_cookie('spotify-redirect', redirect_uri)

    return response


@app.route('/spotify-auth')
def complete_spotify_auth():
    if 'error' in request.args:
        return render_template('failed-authentication.html')

    id = request.cookies['id']

    apis[id]['spotify'] = SpotifyAPI(
        request.args['code'],
        request.cookies['spotify-verifier'],
        request.cookies['spotify-redirect']
    )

    return redirect(unquote(request.args['dest']))


@app.route('/')
def index():
    template = render_template('index.html')
    response = make_response(template)

    id = str(uuid4())
    apis[id] = {service: None for service in services}
    response.set_cookie('id', id)
    return response


@app.route('/load-playlist')
def load_playlist():
    service = request.args['service']
    if service not in services:
        raise ValueError(f'unsupported service: {service}')

    id = request.cookies['id']

    api = apis[id][service]
    if api is None:
        return authenticate(service, redirect=request.full_path)

    return render_template(
        'load-playlist.html', service=service, playlists=api.get_user_playlists()
    )


@app.route('/convert-playlist')
def convert_playlist():
    service = request.args['source']
    if service not in services:
        raise ValueError(f'unsupported service: {service}')

    id = request.cookies['id']
    api = apis[id][service]
    if api is None:
        # TODO: Should we retry authentication?
        raise RuntimeError("couldn't access API")

    template = render_template('convert-playlist.html')
    response = make_response(template)
    songs = '[' + ','.join(song.to_json() for song in api.get_playlist(request.args['id'])) + ']'
    response.set_cookie('songs', songs)
    return response


@app.route('/save-playlist')
def save_playlist():
    service = request.args['service']
    if service not in service:
        raise ValueError(f'unsupported service: {service}')

    id = request.cookies['id']
    api = apis[id][service]
    if api is None:
        return authenticate(service, redirect=request.full_path)

    template = render_template('save-playlist.html')
    response = make_response(template)
    response.set_cookie('service', service)
    return response


@app.route('/save-playlist', methods=['POST'])
def save_playlist_post():
    name = request.form['name']

    service = request.cookies['service']
    if service not in services:
        raise ValueError(f'unsupported service: {service}')

    id = request.cookies['id']
    api = apis[id][service]
    if api is None:
        raise RuntimeError("couldn't access API")

    songs = [Song.from_json(x) for x in request.cookies['songs']]
    api.create_playlist(name, songs)

    return redirect('/')


@app.route('/choose-service')
def choose_service():
    return render_template('choose-service.html', redirect=request.args['redirect'])


auth['spotify']['id'] = get_spotify_client_id()

# Set a secret key so we can use `flask.session`.
app.secret_key = b'.\x93\x9b\x80\xa6\x8b^6-\x03n(\xad\x14xu\x9d1\x8d\xb8!)sr\xf5\x98)\xa4\xc9B+]'
