from crypt import methods
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
app = Flask(__name__)

import psycopg2 as pes
from dotenv import dotenv_values
import json


def pripojenie_na_datab():
    premenna = dotenv_values("/home/peso.env")
    conn = pes.connect(
        host="147.175.150.216",
        database="dota2",
        user=premenna['DBUSER'],
        password=premenna['DBPASS'])
    kurzor = conn.cursor()

    return kurzor

@app.route('/v2/patches/', methods=['GET']) #zadanie2
def v2():
    kurzor = pripojenie_na_datab()
    kurzor.execute('SELECT patches.name as patch_version, '
                   'CAST( extract(epoch FROM patches.release_date) AS INT) as patch_start_date, '
                   'CAST( extract(epoch FROM patch2.release_date) AS INT) as patch_end_date, '
                   'all_matches.match_id, ROUND(all_matches.duration/60.0, 2) '
                   'FROM patches '
                   'LEFT JOIN patches as patch2 on patches.id = patch2.id - 1 '
                   'LEFT JOIN( '
                   'SELECT matches.id as match_id, duration, start_time '
                   'FROM matches '
                   ') as all_matches on all_matches.start_time > extract(epoch FROM patches.release_date) '
                   'and all_matches.start_time < COALESCE(extract(epoch FROM patch2.release_date), 9999999999) '
                   'ORDER by patches.id')

    vystup = {}
    vystup['patches'] = []

    for riadok in kurzor:
        act_patch = None

        for patch in vystup['patches']:
            if patch['patch_version'] == str(riadok[0]):
                act_patch = patch
                break

        if act_patch is not None:
            match = {}
            match['match_id'] = riadok[3]
            match['duration'] = float(riadok[4])

            act_patch['matches'].append(match)
        else:
            act_patch = {}
            act_patch['patch_version'] = str(riadok[0])
            act_patch['patch_start_date'] = riadok[1]
            act_patch['patch_end_date'] = riadok[2]
            act_patch['matches'] = []
            vystup['patches'].append(act_patch)

            if riadok[3] is not None and riadok[4] is not None:
                match = {}
                match['match_id'] = riadok[3]
                match['duration'] = float(riadok[4])
                act_patch['matches'].append(match)

    return json.dumps(vystup)


@app.route('/v2/players/14944/game_exp/', methods=['GET']) #zadanie2
def v2_2():
    print()


@app.route('/v1/health', methods=['GET']) #zadanie 1
def v1health():

    kurzor = pripojenie_na_datab()
    kurzor.execute("SELECT VERSION()")
    vystup = kurzor.fetchone()
    kurzor.execute("SELECT pg_database_size('dota2')/1024/1024 as dota2_db_size")
    vystup2 = kurzor.fetchone()
    jedna = {}
    dva = {}
    jedna['pgsql'] = dva
    dva['version'] = vystup[0]
    dva['dota2_db_size'] = vystup2[0]
    daco = json.dumps(jedna)

    return daco


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