from flask import Flask, Request, jsonify, render_template, request, redirect, url_for
# The below handles some deprecated dependencies in Python > 3.10 that Flask Navigation needs
import collections
import requests
collections.MutableSequence = collections.abc.MutableSequence
collections.Iterable = collections.abc.Iterable
#from flask_navigation import Navigation
# Import Azure SQL helper code
#from azuresqlconnector import *

  
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