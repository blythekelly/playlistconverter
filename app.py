from flask import Flask, Request, jsonify, render_template, request, redirect, url_for
# The below handles some deprecated dependencies in Python > 3.10 that Flask Navigation needs
import collections
import requests
collections.MutableSequence = collections.abc.MutableSequence
collections.Iterable = collections.abc.Iterable
from flask_navigation import Navigation
# Import Azure SQL helper code
from azuresqlconnector import *

  
app = Flask(__name__)

@app.route('/') 
def index():
    return render_template('form-example-home.html')


if __name__ == '__main__': 
    app.run()