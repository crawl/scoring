#!/usr/bin/python

import scload
import query

import logging
from logging import debug, info, warn, error
import crawl_utils
from memoizer import DBMemoizer
import crawl

from scload import query_do, query_first, query_first_col, wrap_transaction
from scload import query_first_def, game_is_win, query_row
from query import count_players_per_day, winners_for_day
from pagedefs import dirty_page, dirty_player, dirty_pages

TOP_N = 1000
MAX_PLAYER_BEST_GAMES = 15
MAX_PLAYER_RECENT_GAMES = 15
MAX_ALL_RECENT_GAMES = 100
MAX_LOW_XL_RUNE_FINDS = 10
MAX_ZIGGURAT_VISITS = 10

# So there are a few problems we have to solve:
# 1. Intercepting new logfile events
#    DONE: parsing a logfile line
#    DONE: dealing with deaths
# 2. Intercepting new milestone events
#    DONE: parsing a milestone line
#    How do we write milestone lines into the db?
# 3. DONE: Collecting data from whereis files
# 4. Determining who is the winner of various competitions based on the
#    ruleset: this still needs to be done for the ones that are basically
#    a complicated query.
# 5. Causing the website to be updated with who is currently winning everything
#    and, if necessary, where players are: first priority is a "who is winning
#    the obvious things"

class OutlineListener (scload.CrawlEventListener):
  def logfile_event(self, cursor, logdict):
    act_on_logfile_line(cursor, logdict)

  def milestone_event(self, cursor, milestone):
    act_on_milestone(cursor, milestone)

  def cleanup(self, db):
    pass

LISTENER = [ OutlineListener() ]

@DBMemoizer
def low_xl_rune_count(c):
  return query_first(c, '''SELECT COUNT(*) FROM low_xl_rune_finds''')

@DBMemoizer
def worst_xl_rune_find(c):
  row = query_row(c, '''SELECT xl, rune_time FROM low_xl_rune_finds
                        ORDER BY xl DESC, rune_time DESC LIMIT 1''')
  return (row[0], row[1])

def add_rune_milestone(c, g):
  if g['type'] != 'rune':
    return
  xl = g['xl']
  rune = scload.extract_rune(g['milestone'])
  if rune == 'abyssal':
    return
  def rinsert():
    query_do(c,
             '''INSERT INTO low_xl_rune_finds (player, start_time,
                                               rune_time, rune, xl)
                     VALUES (%s, %s, %s, %s, %s)''',
             g['name'], g['start'], g['time'], rune, xl)
    dirty_page('overview')

  if low_xl_rune_count(c) >= MAX_LOW_XL_RUNE_FINDS:
    worst_rune = worst_xl_rune_find(c)
    if xl < worst_rune[0]:
      query_do(c, '''DELETE FROM low_xl_rune_finds
                           WHERE xl = %s AND rune_time = %s''',
               *worst_rune)
      rinsert()
  else:
    low_xl_rune_count.flush()
    rinsert()

@DBMemoizer
def player_ziggurat_deepest(c, player):
  return query_first_def(c, 0,
                         '''SELECT deepest FROM ziggurats
                              WHERE player = %s''',
                         player)

@DBMemoizer
def ziggurat_entry_count(c):
  return query_first(c, '''SELECT COUNT(*) FROM ziggurats''')

@DBMemoizer
def ziggurat_row_inferior_to(c, depth):
  return query_first_def(c, 0,
                         '''SELECT id FROM ziggurats
                             WHERE deepest <= %s
                          ORDER BY zig_time LIMIT 1''', depth)

def add_ziggurat_milestone(c, g):
  if not g['type'].startswith('zig'):
    return

  place = g['place']
  mtype = g['type']

  place_matches = scload.R_PLACE_DEPTH.findall(place) or ['1']
  level = int(place_matches[0])
  depth = level * 2
  # Leaving a ziggurat level by the exit gets more props than merely
  # entering the level.
  if mtype == 'zig.exit':
    depth += 1
  player = g['name']
  deepest = player_ziggurat_deepest(c, player)

  def insert():
    query_do(c,
             '''INSERT INTO ziggurats (player, deepest, place, zig_time,
                                       start_time)
                               VALUES (%s, %s, %s, %s, %s)''',
             player, depth, place, g['time'], g['start'])
    player_ziggurat_deepest.flush_key(player)
    dirty_page('overview', 1)

  if deepest:
    if depth >= deepest:
      query_do(c,
               '''UPDATE ziggurats SET deepest = %s, place = %s,
                                       zig_time = %s, start_time = %s
                                 WHERE player = %s''',
               depth, place, g['time'], g['start'], player)
      dirty_page('overview', 1)
  else:
    if ziggurat_entry_count(c) >= MAX_ZIGGURAT_VISITS:
      row = ziggurat_row_inferior_to(c, depth)
      if row:
        query_do(c, '''DELETE FROM ziggurats WHERE id = %s''', row)
        ziggurat_row_inferior_to.flush_key(depth)
        insert()
    else:
      ziggurat_entry_count.flush()
      insert()

def act_on_milestone(c, g):
  add_rune_milestone(c, g)
  add_ziggurat_milestone(c, g)

@DBMemoizer
def topN_count(c):
  return query_first(c, '''SELECT COUNT(*) FROM top_games''')

@DBMemoizer
def lowest_highscore(c):
  return query_first(c, '''SELECT MIN(sc) FROM top_games''')

def insert_game(c, g, table, extras = []):
  cols = scload.LOG_DB_MAPPINGS
  colnames = scload.LOG_DB_SCOLUMNS
  places = scload.LOG_DB_SPLACEHOLDERS
  if extras:
    cols = list(cols)
    for item in extras:
      cols.append([item, item])
    colnames = ",".join([x[1] for x in cols])
    places = ",".join(["%s" for x in cols])
  query_do(c,
           'INSERT INTO %s (%s) VALUES (%s)' %
           (table, colnames, places),
           *[g.get(x[0]) for x in cols])

def update_topN(c, g, n):
  if topN_count(c) >= n:
    if g['sc'] > lowest_highscore(c):
      query_do(c,'''DELETE FROM top_games
                          WHERE id = %s''',
               query_first(c, '''SELECT id FROM top_games
                                  ORDER BY sc LIMIT 1'''))
      insert_game(c, g, 'top_games')
      lowest_highscore.flush()
      dirty_pages('top-N', 'overview')
  else:
    insert_game(c, g, 'top_games')
    dirty_pages('top-N', 'overview')
    topN_count.flush()

@DBMemoizer
def player_best_game_count(c, player):
  return query_first(c, '''SELECT COUNT(*) FROM player_best_games
                                          WHERE name = %s''',
                     player)

@DBMemoizer
def player_lowest_highscore(c, player):
  return query_first(c, '''SELECT MIN(sc) FROM player_best_games
                                         WHERE name = %s''',
                     player)

@DBMemoizer
def player_first_game_exists(c, player):
  return query_first_def(c, False,
                         '''SELECT id FROM player_first_games
                                WHERE name = %s''', player)

@DBMemoizer
def player_recent_game_count(c, player):
  return query_first(c, '''SELECT COUNT(*) FROM player_recent_games
                                          WHERE name = %s''',
                     player)

@DBMemoizer
def all_recent_game_count(c):
  return query_first(c, '''SELECT COUNT(*) FROM all_recent_games''')

@DBMemoizer
def player_streak_is_active(c, player):
  return query_first_def(c, False,
                         '''SELECT active FROM streaks
                                          WHERE player = %s AND active = 1''',
                         player)

def player_won_last_game(c, player):
  return query_first_def(c, False,
                         '''SELECT id FROM player_last_games
                                     WHERE name = %s
                                       AND ktyp='winning' ''',
                         player)

def player_last_game_end_time(c, player):
  return query_first(c, '''SELECT end_time FROM player_last_games
                                          WHERE name = %s''',
                     player)

def player_create_streak(c, player, g):
  query_do(c, '''INSERT INTO streaks
                             (player, start_game_time, end_game_time,
                              active, ngames)
                      VALUES (%s, %s, %s, %s, %s)''',
           player, player_last_game_end_time(c, player), g['end_time'],
           True, 2)

  # Record the game that started the streak:
  query_do(c,
           "INSERT INTO streak_games (" + scload.LOG_DB_SCOLUMNS + ") " +
           "SELECT " + scload.LOG_DB_SCOLUMNS +
           ''' FROM player_last_games WHERE name = %s''', player)

  # And the second game in the streak:
  insert_game(c, g, 'streak_games')

def player_active_streak_id(c, player):
  return query_first(c, '''SELECT id FROM streaks
                                    WHERE player = %s AND active = 1''',
                     player)

def player_break_streak(c, player, g):
  aid = player_active_streak_id(c, player)
  query_do(c, '''UPDATE streaks SET active = 0 WHERE id = %s''', aid)
  g['streak_id'] = aid
  insert_game(c, g, 'streak_breakers', extras = ['streak_id'])

def player_extend_streak(c, player, g):
  query_do(c, '''UPDATE streaks SET end_game_time = %s, ngames = ngames + 1
                              WHERE player = %s AND active = 1''',
           g['end_time'], player)
  insert_game(c, g, 'streak_games')

def update_player_streak(c, g):
  player = g['name']
  win = game_is_win(g)
  if not win:
    if player_streak_is_active(c, player):
      player_break_streak(c, player, g)
      player_streak_is_active.flush_key(player)
      dirty_pages('streaks', 'overview')
      dirty_player(player)
  else:
    if player_streak_is_active(c, player):
      player_extend_streak(c, player, g)
      dirty_pages('streaks', 'overview')
    elif player_won_last_game(c, player):
      player_create_streak(c, player, g)
      dirty_pages('streaks', 'overview')
      player_streak_is_active.flush_key(player)

def update_all_recent_games(c, g):
  if is_junk_game(g):
    return

  dirty_page('recent', 1)
  dirty_page('per-day', 1)
  insert_game(c, g, 'all_recent_games')
  if all_recent_game_count.has_key():
    all_recent_game_count.set_key(all_recent_game_count(c) + 1)

  if all_recent_game_count(c) > MAX_ALL_RECENT_GAMES + 50:
    extra = all_recent_game_count(c) - MAX_ALL_RECENT_GAMES
    ids = query_first_col(c, '''SELECT id FROM all_recent_games
                                 ORDER BY id LIMIT %s''',
                          extra)
    query_do(c, '''DELETE FROM all_recent_games WHERE id IN (%s)''',
             ",".join([str(x) for x in ids]))
    all_recent_game_count.flush_key()

def update_player_recent_games(c, g):
  player = g['name']
  insert_game(c, g, 'player_recent_games')
  if player_recent_game_count.has_key(player):
    player_recent_game_count.set_key(player_recent_game_count(c, player) + 1,
                                     player)
  if player_recent_game_count(c, player) > MAX_PLAYER_RECENT_GAMES + 50:
    extra = player_recent_game_count(c, player) - MAX_PLAYER_RECENT_GAMES
    ids = query_first_col(c, '''SELECT id FROM player_recent_games
                                 WHERE name = %s ORDER BY id LIMIT %s''',
                          player, extra)
    query_do(c, '''DELETE FROM player_recent_games WHERE id IN (%s)''',
             ",".join([str(x) for x in ids]))
    player_recent_game_count.flush_key(player)

def update_player_best_games(c, g):
  player = g['name']
  if player_best_game_count(c, player) >= MAX_PLAYER_BEST_GAMES:
    if g['sc'] > player_lowest_highscore(c, player):
      query_do(c, '''DELETE FROM player_best_games WHERE id = %s''',
               query_first(c, '''SELECT id FROM player_best_games
                                       WHERE name = %s
                                    ORDER BY sc LIMIT 1''',
                           player))
      insert_game(c, g, 'player_best_games')
      player_lowest_highscore.flush_key(player)
  else:
    insert_game(c, g, 'player_best_games')
    player_best_game_count.flush_key(player)

def update_player_char_stats(c, g):
  winc = game_is_win(g) and 1 or 0
  query_do(c, '''INSERT INTO player_char_stats
                             (name, charabbr, games_played, best_xl, wins)
                      VALUES (%s, %s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE games_played = games_played + 1,
                                         best_xl = CASE WHEN best_xl < %s
                                                        THEN %s
                                                        ELSE best_xl END,
                                         wins = wins + %s''',
           g['name'], g['charabbr'], 1, g['xl'], winc,
           g['xl'], g['xl'], winc)

def update_player_first_game(c, g):
  player = g['name']
  if not player_first_game_exists(c, player):
    player_first_game_exists.flush_key(player)
    insert_game(c, g, 'player_first_games')

def update_player_last_game(c, g):
  query_do(c, '''DELETE FROM player_last_games WHERE name = %s''', g['name'])
  insert_game(c, g, 'player_last_games')

def update_wins_table(c, g):
  if game_is_win(g):
    dirty_pages('winners', 'fastest-wins-turns', 'fastest-wins-time',
                'overview')
    insert_game(c, g, 'wins')

def update_player_stats(c, g):
  winc = game_is_win(g) and 1 or 0

  if winc:
    dirty_page('best-players-total-score')
    dirty_page('all-players')
    dirty_player(g['name'])
  else:
    if g['sc'] > 0:
      factor = int(g['sc'] / 40000) + 1
      dirty_page('best-players-total-score', factor)
      dirty_page('all-players', factor)
      dirty_player(g['name'], factor)
    else:
      dirty_player(g['name'], 1)

  query_do(c, '''INSERT INTO players
                             (name, games_played, games_won,
                              total_score, best_score, best_xl,
                              first_game_start, last_game_end, max_runes)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE
                             games_played = games_played + 1,
                             games_won = games_won + %s,
                             total_score = total_score + %s,
                             best_score =
                                   CASE WHEN best_score < %s
                                        THEN %s
                                        ELSE best_score
                                        END,
                             best_xl =
                                   CASE WHEN best_xl < %s
                                        THEN %s
                                        ELSE best_xl
                                        END,
                             max_runes = CASE WHEN max_runes < %s
                                              THEN %s ELSE max_runes END,
                             last_game_end = %s,
                             current_combo = NULL''',
           g['name'], 1, winc, g['sc'], g['sc'], g['xl'], g['start_time'],
           g['end_time'], g['urune'],
           winc, g['sc'], g['sc'], g['sc'], g['xl'], g['xl'],
           g['urune'], g['urune'], g['end_time'])

  # Must be first!
  update_player_streak(c, g)

  update_player_best_games(c, g)
  update_player_char_stats(c, g)
  update_player_recent_games(c, g)
  update_all_recent_games(c, g)
  update_player_first_game(c, g)
  update_player_last_game(c, g)
  update_wins_table(c, g)

def top_score_for_cthing(c, col, table, thing):
  q = "SELECT sc FROM %s WHERE %s = %s" % (table, col, '%s')
  return query_first_def(c, 0, q, thing)

@DBMemoizer
def top_score_for_combo(c, ch):
  return top_score_for_cthing(c, 'charabbr', 'top_combo_scores', ch)

@DBMemoizer
def top_score_for_species(c, sp):
  return top_score_for_cthing(c, 'raceabbr', 'top_species_scores', sp)

@DBMemoizer
def top_score_for_class(c, cls):
  return top_score_for_cthing(c, 'cls', 'top_class_scores', cls)

def update_topscore_table_for(c, g, fn, table, thing):
  sc = g['sc']
  value = g[thing]
  if sc > fn(c, value):
    fn.flush_key(value)
    query_do(c, "DELETE FROM " + table + " WHERE " + thing + " = %s", value)
    insert_game(c, g, table)
    dirty_page('top-combo-scores', 25)
    dirty_page('combo-scoreboard', 25)
    dirty_page('overview', 5)

def update_combo_scores(c, g):
  update_topscore_table_for(c, g, top_score_for_combo,
                            'top_combo_scores', 'charabbr')
  update_topscore_table_for(c, g, top_score_for_species,
                            'top_species_scores', 'raceabbr')
  update_topscore_table_for(c, g, top_score_for_class,
                            'top_class_scores', 'cls')

@DBMemoizer
def ckiller_record_exists(c, ckiller):
  return query_first_def(c, False,
                         '''SELECT id FROM killer_recent_kills
                                     WHERE ckiller = %s''',
                         ckiller)

def update_killer_stats(c, g):
  ckiller = g['ckiller']
  if ckiller != 'winning':
    dirty_page('killers', 1)

  query_do(c, '''INSERT INTO top_killers
                             (ckiller, kills, most_recent_victim)
                      VALUES (%s, %s, %s)
                 ON DUPLICATE KEY UPDATE kills = kills + 1,
                                         most_recent_victim = %s''',
           ckiller, 1, g['name'], g['name'])
  if ckiller_record_exists(c, ckiller):
    query_do(c, '''DELETE FROM killer_recent_kills WHERE ckiller = %s''',
             ckiller)
  else:
    ckiller_record_exists.set_key(True, ckiller)
  insert_game(c, g, 'killer_recent_kills')

def update_gkills(c, g):
  if scload.is_ghost_kill(g):
    dirty_page('gkills', 1)
    ghost = scload.extract_ghost_name(g['killer'])
    if ghost != g['name']:
      query_do(c,
               '''INSERT INTO ghost_victims (ghost, victim) VALUES (%s, %s)''',
               ghost, g['name'])


def is_loser_ktyp(ktyp):
  """The moron games"""
  return ktyp in ['leaving', 'quitting']

def is_junk_game(g):
  ktyp = g['ktyp']
  sc = g['sc']
  return sc < 2500 and is_loser_ktyp(ktyp)


def update_per_day_stats(c, g):
  if is_junk_game(g):
    return

  # Grab just the date portion.
  edate = g['end_time'][:8]
  winc = game_is_win(g) and 1 or 0

  count_players_per_day.flush_key(edate)
  if winc:
    winners_for_day.flush_key(edate)

  query_do(c, '''INSERT INTO per_day_stats (which_day, games_ended,
                                            games_won)
                                    VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                                     games_ended = games_ended + 1,
                                     games_won = games_won + %s''',
           edate, 1, winc, winc)

  player = g['name']
  query_do(c, '''INSERT INTO date_players (which_day, which_month, player,
                                           games, wins)
                                   VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                                        games = games + 1,
                                        wins = wins + %s''',
           edate, edate[:6], player, 1, winc, winc)

def is_known_cthing(c, table, key, value):
  return query_first_def(c, False,
                         "SELECT " + key + " FROM " + table +
                         " WHERE " + key + " = %s",
                         value)

@DBMemoizer
def is_known_race(c, race):
  return is_known_cthing(c, 'known_races', 'race', race)

@DBMemoizer
def is_known_class(c, cls):
  return is_known_cthing(c, 'known_classes', 'cls', cls)

def record_known_thing(c, table, key, value):
  query_do(c, "INSERT INTO " + table + " (" + key + ") " +
           " VALUES (%s)", value)

def update_known_races_classes(c, g):
  race = g['raceabbr']
  cls = g['clsabbr']
  if not is_known_race(c, race):
    record_known_thing(c, 'known_races', 'race', race)
    is_known_race.set_key(True, race)
    query.all_races.flush()
  if not is_known_class(c, cls):
    record_known_thing(c, 'known_classes', 'cls', cls)
    is_known_class.set_key(True, cls)
    query.all_classes.flush()

def act_on_logfile_line(c, this_game):
  """Actually assign things and write to the db based on a logfile line
  coming through. All lines get written to the db; some will assign
  irrevocable points and those should be assigned immediately. Revocable
  points (high scores, lowest dungeon level, fastest wins) should be
  calculated elsewhere."""

  if 'start_time' not in this_game:
    return

  # Update top-1000.
  update_topN(c, this_game, TOP_N)

  # Update statistics for this player's game.
  update_player_stats(c, this_game)
  update_combo_scores(c, this_game)
  update_killer_stats(c, this_game)
  update_gkills(c, this_game)
  update_per_day_stats(c, this_game)
  update_known_races_classes(c, this_game)
