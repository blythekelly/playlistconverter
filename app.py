from base64 import urlsafe_b64encode
from hashlib import sha256
import secrets
from urllib.parse import quote, unquote, urlencode

from flask import Flask, redirect, render_template, request, session

from apis import API, SpotifyAPI
from apis.song import Song


app = Flask(__name__)

apis: dict[str, API | None] = {
    'spotify': None,
}

# temporary workaround to share state between functions for
# authentication
auth = {service: {} for service in apis}


def get_spotify_client_id() -> str:
    # TODO: Use Azure Key Vault.
    with open('keys/spotify/id') as file:
        return file.readline()


def authenticate(service: str, redirect: str):
    authenticators = {
        'spotify': authenticate_spotify,
    }

    authenticator = authenticators[service]
    return authenticator(redirect)


def authenticate_spotify(dest: str):
    verifier = secrets.token_urlsafe(100)[:64].encode()
    challenge = urlsafe_b64encode(sha256(verifier).digest()).decode().rstrip('=')

    redirect_uri = f'http://127.0.0.1:5000/spotify-auth?dest={quote(dest, safe='')}'

    params = urlencode({
            'client_id': auth['spotify']['id'],
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
            'scope': 'playlist-modify-public playlist-modify-private playlist-read-private',
            # TODO: Add 'state': <value>,
    })

    auth['spotify']['verifier'] = verifier
    auth['spotify']['redirect'] = redirect_uri

    URL = 'https://accounts.spotify.com/authorize'
    return redirect(URL + '?' + params)


@app.route('/spotify-auth')
def complete_spotify_auth():
    if 'error' in request.args:
        return render_template('failed-authentication.html')

    apis['spotify'] = SpotifyAPI(
        request.args['code'],
        auth['spotify']['verifier'],
        auth['spotify']['redirect']
    )

    return redirect(unquote(request.args['dest']))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/load-playlist')
def load_playlist():
    service = request.args['service']
    if service not in apis:
        raise ValueError(f'unsupported service: {service}')

    api = apis[service]
    if api is None:
        return authenticate(service, redirect=request.full_path)

    return render_template('load-playlist.html', service=service, playlists=api.get_user_playlists())


@app.route('/convert-playlist')
def convert_playlist():
    service = request.args['source']
    if service not in apis:
        raise ValueError(f'unsupported service: {service}')

    api = apis[service]
    if api is None:
        # TODO: Should we retry authentication?
        raise RuntimeError("couldn't access API")

    session['songs'] = api.get_playlist(request.args['id'])
    return render_template('convert-playlist.html')


@app.route('/save-playlist')
def save_playlist():
    service = request.args['service']
    if service not in apis:
        raise ValueError(f'unsupported service: {service}')

    api = apis[service]
    if api is None:
        return authenticate(service, redirect=request.full_path)

    session['service'] = service

    return render_template('save-playlist.html')


@app.route('/save-playlist', methods=['POST'])
def save_playlist_post():
    name = request.form['name']

    service = session['service']
    if service not in apis:
        raise ValueError(f'unsupported service: {service}')

    api = apis[service]
    if api is None:
        raise RuntimeError("couldn't access API")

    api.create_playlist(name, [Song(**song) for song in session['songs']])
    return redirect('/')


@app.route('/choose-service')
def choose_service():
    return render_template('choose-service.html', redirect=request.args['redirect'])


if __name__ == '__main__':
    auth['spotify']['id'] = get_spotify_client_id()

    # Set a secret key so we can use `flask.session`.
    with open('keys/flask/secret', 'rb') as file:
        app.secret_key = file.readline()

    app.run(debug=True)
