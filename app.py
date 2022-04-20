from crypt import methods
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
app = Flask(__name__)

import psycopg2 as pes
from dotenv import dotenv_values
import json


def pripojenie(): #pripojenie na databazu
    premenna = dotenv_values("/home/peso.env")
    conn = pes.connect(
        host="147.175.150.216",
        database="dota2",
        user=premenna['DBUSER'],
        password=premenna['DBPASS'])
    kurzor = conn.cursor()

    return kurzor


@app.route('/v3/matches/<string:match_id>/top_purchases/', methods=['GET'])
def v3_1(match_id):
    kurzor = pripojenie()
    kurzor.execute("SELECT ssub.hero_id, ssub.localized_name, ssub.item_count, ssub.item_id, ssub.item_name FROM "
                    "(SELECT sub.localized_name, sub.item_name, sub.hero_id, sub.item_id,"
                    "sub.item_count, row_number() over (partition by sub.localized_name order by sub.hero_id, sub.item_count DESC, sub.item_name) as r_num "
                    "FROM("
                    "SELECT mpd.match_id, hr.localized_name, hr.id as hero_id, it.id as item_id,"
                    "((manchr.radiant_win AND mpd.player_slot <= 4) OR (not manchr.radiant_win AND mpd.player_slot >= 128)) as winner, "
                    "it.name AS item_name, count (it.name) as item_count "
                    "FROM purchase_logs AS pl "
                    "JOIN matches_players_details AS mpd ON mpd.id = pl.match_player_detail_id "
                    "JOIN items AS it ON it.id = pl.item_id "
                    "JOIN heroes AS hr ON hr.id = mpd.hero_id "
                    "JOIN matches as manchr on manchr.id = mpd.match_id "
                    "WHERE manchr.id = " + match_id +
                    "GROUP BY mpd.match_id, hr.localized_name, item_name, mpd.hero_id, manchr.radiant_win, winner, mpd.player_slot, hr.id, it.id"
                    "ORDER BY mpd.hero_id, item_count DESC, it.name) AS sub "
                    "WHERE winner = true order by sub.hero_id, sub.item_count DESC, sub.item_name) AS ssub "
                    "WHERE ssub.r_num <= 5)")
    vystup = {}
    for riadok in kurzor:
        vystup = riadok

    return json.dumps(vystup)

@app.route('/v2/patches/', methods=['GET']) # zadanie3 2v1
def v2_1():
    kurzor = pripojenie()
    kurzor.execute('SELECT patches.name as patch_version, '
                   'CAST( extract(epoch FROM patches.release_date) as INT) as patch_start_date, '
                   'CAST( extract(epoch FROM patch2.release_date) as INT) as patch_end_date, '
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


@app.route('/v2/players/<string:player_id>/game_exp/', methods=['GET']) #  2v1
def v2_2(player_id):
    kurzor = pripojenie()
    kurzor.execute("SELECT COALESCE(nick, 'unknown') "
                   "FROM players "
                   "WHERE id = " + player_id)

    vystup = {}
    vystup['id'] = int(player_id)
    vystup['player_nick'] = kurzor.fetchone()[0]

    kurzor.execute("SELECT vysledok.match_id, vysledok.h_name as hero_localized_name, "
                   "vysledok.min as match_duration_minutes, vysledok.experiences_gained, "
                   "vysledok.level_gained, "
                   "CASE WHEN side_played = 'radiant' and vysledok.radiant_win = 'true' OR "
                   "side_played = 'dire' and vysledok.radiant_win = 'false' "
                   "THEN true ELSE false END as winner "
                   "FROM ("
                   "SELECT players.id as pid, COALESCE(nick, 'unknown') as player_nick, heroes.localized_name as h_name, "
                   "matches.id as match_id, matches.duration, ROUND(matches.duration/60.0, 2) as min, "
                   "mpd.level as level_gained, "
                   "COALESCE(mpd.xp_hero, 0) + COALESCE(mpd.xp_creep, 0) + "
                   "COALESCE(mpd.xp_other, 0) + COALESCE(mpd.xp_roshan, 0) as experiences_gained, "
                   "mpd.player_slot, "
                   "CASE WHEN mpd.player_slot < 5 THEN 'radiant' ELSE 'dire' END as side_played, "
                   "matches.radiant_win "
                   "FROM matches_players_details as mpd "
                   "JOIN players ON players.id = mpd.player_id "
                   "JOIN heroes ON heroes.id = mpd.hero_id "
                   "JOIN matches ON matches.id = mpd.match_id "
                   "WHERE players.id = " + player_id +
                    " ORDER BY matches.id"
                   ") as vysledok")

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


@app.route('/v2/players/<string:player_id>/game_objectives/', methods=['GET']) # zadanie3 2v1
def v2_3(player_id):
    kurzor = pripojenie()

    vystup = {}
    vystup['id'] = int(player_id)

    kurzor.execute("SELECT p.id, COALESCE(p.nick, 'unknown') AS player_nick, "
                   "mpd.match_id, heroes.localized_name, "
                   "COALESCE(game_objectives.subtype, 'NO_ACTION') "
                   "FROM players AS p "
                   "LEFT JOIN matches_players_details AS mpd ON mpd.player_id = p.id "
                   "LEFT JOIN heroes ON heroes.id = mpd.hero_id "
                   "LEFT JOIN game_objectives ON game_objectives.match_player_detail_id_1 = mpd.id "
                   "WHERE p.id = " + player_id +
                   " ORDER BY mpd.match_id, subtype")

    matches = []

    for riadok in kurzor:
        if not 'player_nick' in vystup.keys():
            vystup['player_nick'] = riadok[1]

        aktulny_match = None
        for match in matches:
            if match['match_id'] == riadok[2]:
                aktulny_match = match
                break

        if aktulny_match is not None:
            aktualna_akcia = None
            for akcia in aktulny_match['actions']:
                if akcia['hero_action'] == riadok[4]:
                    aktualna_akcia = akcia
                    break

            if aktualna_akcia is not None:
                aktualna_akcia['count'] += 1
            else:
                aktualna_akcia = {}
                aktualna_akcia['hero_action'] = riadok[4]
                aktualna_akcia['count'] = 1
                aktulny_match['actions'].append(aktualna_akcia)

        else:
            aktulny_match = {}
            aktulny_match['match_id'] = riadok[2]
            aktulny_match['hero_localized_name'] = riadok[3]
            matches.append(aktulny_match)

            aktulny_match['actions'] = []
            akcia = {}
            akcia['hero_action'] = riadok[4]
            akcia['count'] = 1
            aktulny_match['actions'].append(akcia)

    vystup['matches'] = matches

    kurzor.close()

    return json.dumps(vystup)


@app.route('/v1/health', methods=['GET']) # zadanie 2
def v1health():

    kurzor = pripojenie()
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