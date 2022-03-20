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
    kurzor.execute('SELECT matches.id as match_id, duration, all_patches.patch_version, all_patches.patch_start_date, all_patches.patch_end_date '
                   'FROM matches '
                   'LEFT JOIN( '
                   'SELECT patches.name as patch_version, extract(epoch FROM patches.release_date) as patch_start_date, extract(epoch FROM patch2.release_date) as patch_end_date '
                   'FROM patches '
                   'LEFT JOIN patches as patch2 on patches.id = patch2.id - 1 '
                   'ORDER by patches.id '
                   ') as all_patches on matches.start_time > all_patches.patch_start_date and matches.start_time < COALESCE(all_patches.patch_end_date, 9999999999)')

    vystup = {}
    vystup['patches'] = []

    for riadok in kurzor:
        act_patch = None

        for patch in vystup['patches']:
            if patch['patch_version'] == str(riadok[2]):
                act_patch = patch
                break

        if act_patch is not None:
            match = {}
            match['match_id'] = riadok[0]
            match['duration'] = riadok[1]

            act_patch['matches'].append(match)
        else:
            act_patch = {}
            act_patch['patch_version'] = riadok[0]
            act_patch['patch_start_date'] = riadok[1]
            act_patch['patch_end_date'] = riadok[2]
            act_patch['matches'] = []
            vystup['patches'].append(act_patch)

            match = {}
            match['match_id'] = riadok[3]
            match['duration'] = riadok[4]
            act_patch['matches'].append(match)

    return json.dumps(vystup)


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