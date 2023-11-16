from flask import Flask, render_template


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/library')
def library():
    return render_template('library.html')


@app.route('/parse')
def parse():
    return render_template('parse.html')


@app.route('/login')
def login():
    return render_template('login.html')


if __name__ == '__main__':
    app.run()
