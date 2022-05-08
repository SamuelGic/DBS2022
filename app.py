from crypt import methods
from datetime import datetime

import sqlalchemy as sqlalchemy
from flask import Flask, render_template, request, redirect, url_for, Response

app = Flask(__name__)

import psycopg2 as pes
from dotenv import dotenv_values
import json
from sqlalchemy import sql
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, Numeric, \
    SmallInteger, String, Table, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


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


@app.route('/v2/patches/', methods=['GET'])  # zadanie3 2v1
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


@app.route('/v2/players/<string:player_id>/game_exp/', methods=['GET'])  # 2v1
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


@app.route('/v2/players/<string:player_id>/game_objectives/', methods=['GET'])  # zadanie3 2v1
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


@app.route('/v1/health', methods=['GET'])  # zadanie 2
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


@app.route('/v4/patches/', methods=['GET'])
def orm_patches():
    ab = Patch.query.all()
    for a in ab:
        print(a.id, a.duration)
        #print()

    return Response(json.dumps("fck"), status=200, mimetype="application/json")


Base = declarative_base()
metadata = Base.metadata


daco_env = dotenv_values("/home/peso.env")
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://' + daco_env['DBUSER'] + ':' + daco_env['DBPASS'] + '@147.175.150.216/dota2'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = sqlalchemy(app)


class Ability(db.Model):
    _tablename_ = 'abilities'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)


class AuthGroup(db.Model):
    _tablename_ = 'auth_group'

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('auth_group_id_seq'::regclass)"))
    name = db.Column(db.String(150), nullable=False, unique=True)


class AuthUser(db.Model):
    _tablename_ = 'auth_user'

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('auth_user_id_seq'::regclass)"))
    password = db.Column(db.String(128), nullable=False)
    last_login = db.Column(db.DateTime(True))
    is_superuser = db.Column(db.Boolean, nullable=False)
    username = db.Column(db.String(150), nullable=False, unique=True)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    is_staff = db.Column(db.Boolean, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False)
    date_joined = db.Column(db.DateTime(True), nullable=False)


class ClusterRegion(db.Model):
    _tablename_ = 'cluster_regions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)


class DjangoContentType(db.Model):
    _tablename_ = 'django_content_type'
    _table_args_ = (
        UniqueConstraint('app_label', 'model'),
    )

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('django_content_type_id_seq'::regclass)"))
    app_label = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)


class DjangoMigration(db.Model):
    _tablename_ = 'django_migrations'

    id = db.Column(db.BigInteger, primary_key=True, server_default=text("nextval('django_migrations_id_seq'::regclass)"))
    app = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    applied = db.Column(db.DateTime(True), nullable=False)


class DjangoSession(db.Model):
    _tablename_ = 'django_session'

    session_key = db.Column(db.String(40), primary_key=True, index=True)
    session_data = db.Column(db.Text, nullable=False)
    expire_date = db.Column(db.DateTime(True), nullable=False, index=True)


class DoctrineMigrationVersion(db.Model):
    _tablename_ = 'doctrine_migration_versions'

    version = db.Column(db.String(191), primary_key=True)
    executed_at = db.Column(db.TIMESTAMP(), server_default=text("NULL::timestamp without time zone"))
    execution_time = db.Column(db.Integer)


class FlywaySchemaHistory(db.Model):
    _tablename_ = 'flyway_schema_history'

    installed_rank = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(50))
    description = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    script = db.Column(db.String(1000), nullable=False)
    checksum = db.Column(db.Integer)
    installed_by = db.Column(db.String(100), nullable=False)
    installed_on = db.Column(db.DateTime, nullable=False, server_default=text("now()"))
    execution_time = db.Column(db.Integer, nullable=False)
    success = db.Column(db.Boolean, nullable=False, index=True)


class Hero(db.Model):
    _tablename_ = 'heroes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    localized_name = db.Column(db.Text)


class Item(db.Model):
    _tablename_ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)


class Migration(db.Model):
    _tablename_ = 'migrations'

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('migrations_id_seq'::regclass)"))
    migration = db.Column(db.String(255), nullable=False)
    batch = db.Column(db.Integer, nullable=False)


class Patch(db.Model):
    _tablename_ = 'patches'

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('patches_id_seq'::regclass)"))
    name = db.Column(db.Text, nullable=False)
    release_date = db.Column(db.DateTime, nullable=False)


class Player(db.Model):
    _tablename_ = 'players'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    nick = db.Column(db.Text)


t_propel_migration = Table(
    'propel_migration', metadata,
    db.Column('version', db.Integer, server_default=text("0"))
)


class AuthPermission(db.Model):
    _tablename_ = 'auth_permission'
    _table_args_ = (
        UniqueConstraint('content_type_id', 'codename'),
    )

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('auth_permission_id_seq'::regclass)"))
    name = db.Column(db.String(255), nullable=False)
    content_type_id = db.Column(db.ForeignKey('django_content_type.id', deferrable=True, initially='DEFERRED'), nullable=False, index=True)
    codename = db.Column(db.String(100), nullable=False)

    content_type = db.relationship('DjangoContentType')


class AuthUserGroup(db.Model):
    _tablename_ = 'auth_user_groups'
    _table_args_ = (
        UniqueConstraint('user_id', 'group_id'),
    )

    id = db.Column(db.BigInteger, primary_key=True, server_default=text("nextval('auth_user_groups_id_seq'::regclass)"))
    user_id = db.Column(db.ForeignKey('auth_user.id', deferrable=True, initially='DEFERRED'), nullable=False, index=True)
    group_id = db.Column(db.ForeignKey('auth_group.id', deferrable=True, initially='DEFERRED'), nullable=False, index=True)

    group = db.relationship('AuthGroup')
    user = db.relationship('AuthUser')


class DjangoAdminLog(db.Model):
    _tablename_ = 'django_admin_log'
    _table_args_ = (
        CheckConstraint('action_flag >= 0'),
    )

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('django_admin_log_id_seq'::regclass)"))
    action_time = db.Column(db.DateTime(True), nullable=False)
    object_id = db.Column(db.Text)
    object_repr = db.Column(db.String(200), nullable=False)
    action_flag = db.Column(db.SmallInteger, nullable=False)
    change_message = db.Column(db.Text, nullable=False)
    content_type_id = db.Column(db.ForeignKey('django_content_type.id', deferrable=True, initially='DEFERRED'), index=True)
    user_id = db.Column(db.ForeignKey('auth_user.id', deferrable=True, initially='DEFERRED'), nullable=False, index=True)

    content_type = db.relationship('DjangoContentType')
    user = db.relationship('AuthUser')


class Match(db.Model):
    _tablename_ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    cluster_region_id = db.Column(db.ForeignKey('cluster_regions.id'))
    start_time = db.Column(db.Integer)
    duration = db.Column(db.Integer)
    tower_status_radiant = db.Column(db.Integer)
    tower_status_dire = db.Column(db.Integer)
    barracks_status_radiant = db.Column(db.Integer)
    barracks_status_dire = db.Column(db.Integer)
    first_blood_time = db.Column(db.Integer)
    game_mode = db.Column(db.Integer)
    radiant_win = db.Column(db.Boolean)
    negative_votes = db.Column(db.Integer)
    positive_votes = db.Column(db.Integer)

    cluster_region = db.relationship('ClusterRegion')


class PlayerRating(db.Model):
    _tablename_ = 'player_ratings'

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('player_ratings_id_seq'::regclass)"))
    player_id = db.Column(db.ForeignKey('players.id'))
    total_wins = db.Column(db.Integer)
    total_matches = db.Column(db.Integer)
    trueskill_mu = db.Column(db.Numeric)
    trueskill_sigma = db.Column(db.Numeric)

    player = db.relationship('Player')


class AuthGroupPermission(db.Model):
    _tablename_ = 'auth_group_permissions'
    _table_args_ = (
        UniqueConstraint('group_id', 'permission_id'),
    )

    id = db.Column(db.BigInteger, primary_key=True, server_default=text("nextval('auth_group_permissions_id_seq'::regclass)"))
    group_id = db.Column(db.ForeignKey('auth_group.id', deferrable=True, initially='DEFERRED'), nullable=False, index=True)
    permission_id = db.Column(db.ForeignKey('auth_permission.id', deferrable=True, initially='DEFERRED'), nullable=False, index=True)

    group = db.relationship('AuthGroup')
    permission = db.relationship('AuthPermission')


class AuthUserUserPermission(db.Model):
    _tablename_ = 'auth_user_user_permissions'
    _table_args_ = (
        UniqueConstraint('user_id', 'permission_id'),
    )

    id = db.Column(db.BigInteger, primary_key=True, server_default=text("nextval('auth_user_user_permissions_id_seq'::regclass)"))
    user_id = db.Column(db.ForeignKey('auth_user.id', deferrable=True, initially='DEFERRED'), nullable=False, index=True)
    permission_id = db.Column(db.ForeignKey('auth_permission.id', deferrable=True, initially='DEFERRED'), nullable=False, index=True)

    permission = db.relationship('AuthPermission')
    user = db.relationship('AuthUser')


class MatchesPlayersDetail(db.Model):
    _tablename_ = 'matches_players_details'
    _table_args_ = (
        Index('idx_match_id_player_id', 'match_id', 'player_slot', 'id'),
    )

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('matches_players_details_id_seq'::regclass)"))
    match_id = db.Column(db.ForeignKey('matches.id'))
    player_id = db.Column(db.ForeignKey('players.id'))
    hero_id = db.Column(db.ForeignKey('heroes.id'))
    player_slot = db.Column(db.Integer)
    gold = db.Column(db.Integer)
    gold_spent = db.Column(db.Integer)
    gold_per_min = db.Column(db.Integer)
    xp_per_min = db.Column(db.Integer)
    kills = db.Column(db.Integer)
    deaths = db.Column(db.Integer)
    assists = db.Column(db.Integer)
    denies = db.Column(db.Integer)
    last_hits = db.Column(db.Integer)
    stuns = db.Column(db.Integer)
    hero_damage = db.Column(db.Integer)
    hero_healing = db.Column(db.Integer)
    tower_damage = db.Column(db.Integer)
    item_id_1 = db.Column(db.ForeignKey('items.id'))
    item_id_2 = db.Column(db.ForeignKey('items.id'))
    item_id_3 = db.Column(db.ForeignKey('items.id'))
    item_id_4 = db.Column(db.ForeignKey('items.id'))
    item_id_5 = db.Column(db.ForeignKey('items.id'))
    item_id_6 = db.Column(db.ForeignKey('items.id'))
    level = db.Column(db.Integer)
    leaver_status = db.Column(db.Integer)
    xp_hero = db.Column(db.Integer)
    xp_creep = db.Column(db.Integer)
    xp_roshan = db.Column(db.Integer)
    xp_other = db.Column(db.Integer)
    gold_other = db.Column(db.Integer)
    gold_death = db.Column(db.Integer)
    gold_abandon = db.Column(db.Integer)
    gold_sell = db.Column(db.Integer)
    gold_destroying_structure = db.Column(db.Integer)
    gold_killing_heroes = db.Column(db.Integer)
    gold_killing_creeps = db.Column(db.Integer)
    gold_killing_roshan = db.Column(db.Integer)
    gold_killing_couriers = db.Column(db.Integer)

    hero = db.relationship('Hero')
    item = db.relationship('Item', primaryjoin='MatchesPlayersDetail.item_id_1 == Item.id')
    item1 = db.relationship('Item', primaryjoin='MatchesPlayersDetail.item_id_2 == Item.id')
    item2 = db.relationship('Item', primaryjoin='MatchesPlayersDetail.item_id_3 == Item.id')
    item3 = db.relationship('Item', primaryjoin='MatchesPlayersDetail.item_id_4 == Item.id')
    item4 = db.relationship('Item', primaryjoin='MatchesPlayersDetail.item_id_5 == Item.id')
    item5 = db.relationship('Item', primaryjoin='MatchesPlayersDetail.item_id_6 == Item.id')
    match = db.relationship('Match')
    player = db.relationship('Player')


class Teamfight(db.Model):
    _tablename_ = 'teamfights'
    _table_args_ = (
        Index('teamfights_match_id_start_teamfight_id_idx', 'match_id', 'start_teamfight', 'id'),
    )

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('teamfights_id_seq'::regclass)"))
    match_id = db.Column(db.ForeignKey('matches.id'))
    start_teamfight = db.Column(db.Integer)
    end_teamfight = db.Column(db.Integer)
    last_death = db.Column(db.Integer)
    deaths = db.Column(db.Integer)

    match = db.relationship('Match')


class AbilityUpgrade(db.Model):
    _tablename_ = 'ability_upgrades'

    id = db.Column(Integer, primary_key=True, server_default=text("nextval('ability_upgrades_id_seq'::regclass)"))
    ability_id = db.Column(db.ForeignKey('abilities.id'))
    match_player_detail_id = db.Column(db.ForeignKey('matches_players_details.id'))
    level = db.Column(Integer)
    time = db.Column(Integer)

    ability = db.relationship('Ability')
    match_player_detail = db.relationship('MatchesPlayersDetail')


class Chat(db.Model):
    _tablename_ = 'chats'

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('chats_id_seq'::regclass)"))
    match_player_detail_id = db.Column(db.ForeignKey('matches_players_details.id'))
    message = db.Column(db.Text)
    time = db.Column(db.Integer)
    nick = db.Column(db.Text)

    match_player_detail = relationship('MatchesPlayersDetail')


class GameObjective(db.Model):
    _tablename_ = 'game_objectives'

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('game_objectives_id_seq'::regclass)"))
    match_player_detail_id_1 = db.Column(db.ForeignKey('matches_players_details.id'))
    match_player_detail_id_2 = db.Column(db.ForeignKey('matches_players_details.id'))
    key = db.Column(db.Integer)
    subtype = db.Column(db.Text)
    team = db.Column(db.Integer)
    time = db.Column(db.Integer)
    value = db.Column(db.Integer)
    slot = db.Column(db.Integer)

    matches_players_detail = db.relationship('MatchesPlayersDetail', primaryjoin='GameObjective.match_player_detail_id_1 == MatchesPlayersDetail.id')
    matches_players_detail1 = db.relationship('MatchesPlayersDetail', primaryjoin='GameObjective.match_player_detail_id_2 == MatchesPlayersDetail.id')


class PlayerAction(db.Model):
    _tablename_ = 'player_actions'

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('player_actions_id_seq'::regclass)"))
    unit_order_none = db.Column(db.Integer)
    unit_order_move_to_position = db.Column(db.Integer)
    unit_order_move_to_target = db.Column(db.Integer)
    unit_order_attack_move = db.Column(db.Integer)
    unit_order_attack_target = db.Column(db.Integer)
    unit_order_cast_position = db.Column(db.Integer)
    unit_order_cast_target = db.Column(db.Integer)
    unit_order_cast_target_tree = db.Column(db.Integer)
    unit_order_cast_no_target = db.Column(db.Integer)
    unit_order_cast_toggle = db.Column(db.Integer)
    unit_order_hold_position = db.Column(db.Integer)
    unit_order_train_ability = db.Column(db.Integer)
    unit_order_drop_item = db.Column(db.Integer)
    unit_order_give_item = db.Column(db.Integer)
    unit_order_pickup_item = db.Column(db.Integer)
    unit_order_pickup_rune = db.Column(db.Integer)
    unit_order_purchase_item = db.Column(db.Integer)
    unit_order_sell_item = db.Column(db.Integer)
    unit_order_disassemble_item = db.Column(db.Integer)
    unit_order_move_item = db.Column(db.Integer)
    unit_order_cast_toggle_auto = db.Column(db.Integer)
    unit_order_stop = db.Column(db.Integer)
    unit_order_buyback = db.Column(db.Integer)
    unit_order_glyph = db.Column(db.Integer)
    unit_order_eject_item_from_stash = db.Column(db.Integer)
    unit_order_cast_rune = db.Column(db.Integer)
    unit_order_ping_ability = db.Column(db.Integer)
    unit_order_move_to_direction = db.Column(db.Integer)
    match_player_detail_id = db.Column(db.ForeignKey('matches_players_details.id'))

    match_player_detail = db.relationship('MatchesPlayersDetail')


class PlayerTime(db.Model):
    _tablename_ = 'player_times'

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('player_times_id_seq'::regclass)"))
    match_player_detail_id = db.Column(ForeignKey('matches_players_details.id'))
    time = db.Column(db.Integer)
    gold = db.Column(db.Integer)
    lh = db.Column(db.Integer)
    xp = db.Column(db.Integer)

    match_player_detail = db.relationship('MatchesPlayersDetail')


class PurchaseLog(db.Model):
    _tablename_ = 'purchase_logs'

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('purchase_logs_id_seq'::regclass)"))
    match_player_detail_id = db.Column(db.ForeignKey('matches_players_details.id'))
    item_id = db.Column(db.ForeignKey('items.id'))
    time = db.Column(db.Integer)

    item = db.relationship('Item')
    match_player_detail = db.relationship('MatchesPlayersDetail')


class TeamfightsPlayer(db.Model):
    _tablename_ = 'teamfights_players'

    id = db.Column(db.Integer, primary_key=True, server_default=text("nextval('teamfights_players_id_seq'::regclass)"))
    teamfight_id = db.Column(db.ForeignKey('teamfights.id'))
    match_player_detail_id = db.Column(db.ForeignKey('matches_players_details.id'))
    buyback = db.Column(db.Integer)
    damage = db.Column(db.Integer)
    deaths = db.Column(db.Integer)
    gold_delta = db.Column(db.Integer)
    xp_start = db.Column(db.Integer)
    xp_end = db.Column(db.Integer)

    match_player_detail = db.relationship('MatchesPlayersDetail')
    teamfight = db.relationship('Teamfight')


if __name__ == '__main__':
   app.run()