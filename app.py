from crypt import methods
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
app = Flask(__name__)

import psycopg2 as pes
from dotenv import dotenv_values
import json

@app.route('/v1/health', methods=['GET'])
def v1health():
   premenna = dotenv_values("/home")
   conn = pes.connect(
    host="localhost",
    database="suppliers",
    user=['DBUSER'],
    password=['DBPASS'])


@app.route('/hello', methods=['POST'])
def hello():
   name = request.form.get('name')

   if name:
       print('Request for hello page received with name=%s' % name)
       return render_template('hello.html', name = name)
   else:
       print('Request for hello page received with no name or blank name -- redirecting')
       return redirect(url_for('index'))

@app.route('/')
def index():
   print('Request for index page received')
   return render_template('index.html')

if __name__ == '__main__':
   app.run()