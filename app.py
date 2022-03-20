from crypt import methods
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
app = Flask(__name__)

import psycopg2 as pes
from dotenv import dotenv_values
import json


def pripojenie_na_datab(): #pripojenie na databazu
    premenna = dotenv_values("/home/peso.env")
    conn = pes.connect(
        host="147.175.150.216",
        database="dota2",
        user=premenna['DBUSER'],
        password=premenna['DBPASS'])
    kurzor = conn.cursor()

    return kurzor

@app.route('/v2/patches/', methods=['GET']) #zadanie2 2v1
def v2_1():
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


@app.route('/v2/players/<string:player_id>/game_exp/', methods=['GET'])
def v2_game_exp(player_id):
    kurzor = pripojenie_na_datab()
    kurzor.execute("SELECT COALESCE(nick, 'unknown') "
                   "FROM players "
                   "WHERE id = " + player_id)

    vystup = {}
    vystup['id'] = int(player_id)
    vystup['player_nick'] = kurzor.fetchone()[0]

    kurzor.execute("SELECT vysledok.match_id, vysledok.h_name AS hero_localized_name, "
                   "vysledok.min AS match_duration_minutes, vysledok.experiences_gained, "
                   "vysledok.level_gained, "
                   "CASE WHEN side_played = 'radiant' AND vysledok.radiant_win = 'true' OR "
                   "side_played = 'dire' AND vysledok.radiant_win = 'false' "
                   "THEN true ELSE false END AS winner "
                   "FROM ("
                   "SELECT players.id AS pid, COALESCE(nick, 'unknown') AS player_nick, heroes.localized_name AS h_name, "
                   "matches.id AS match_id, matches.duration, ROUND(matches.duration/60.0, 2) AS min, "
                   "mpd.level AS level_gained, "
                   "COALESCE(mpd.xp_hero, 0) + COALESCE(mpd.xp_creep, 0) + "
                   "COALESCE(mpd.xp_other, 0) + COALESCE(mpd.xp_roshan, 0) AS experiences_gained, "
                   "mpd.player_slot, "
                   "CASE WHEN mpd.player_slot < 5 THEN 'radiant' ELSE 'dire' END AS side_played, "
                   "matches.radiant_win "
                   "FROM matches_players_details AS mpd "
                   "JOIN players ON players.id = mpd.player_id "
                   "JOIN heroes ON heroes.id = mpd.hero_id "
                   "JOIN matches ON matches.id = mpd.match_id "
                   "WHERE players.id = " + player_id +
                    " ORDER BY matches.id"
                   ") AS vysledok")

    matches = []

    for row in kurzor:
        match = {}
        match['match_id'] = row[0]
        match['hero_localized_name'] = row[1]
        match['match_duration_minutes'] = float(row[2])
        match['experiences_gained'] = row[3]
        match['level_gained'] = row[4]
        match['winner'] = row[5]

        matches.append(match)

    vystup['matches'] = matches

    kurzor.close()

    return json.dumps(vystup)


@app.route('/v2/players/14944/game_objectives/', methods=['GET']) #zadanie2 2v3
def v2_3():
    kurzor = pripojenie_na_datab()
    kurzor.execute()


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