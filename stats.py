#!/usr/bin/python
import MySQLdb

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

# don't add player_recent_games to this list, or duplicate detection won't work
# right
NO_BUGGY_GAMES = {'streak_games', 'streak_breakers', 'wins', 'top_games', 'top_combo_scores',
                  'top_species_scores', 'top_class_scores'}

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
  if table in NO_BUGGY_GAMES and g.get('game_key') in scload.BUGGY_GAMES:
    info('Ignoring buggy game %s for %s', g.get('game_key'), table)
    return False
  try:
    scload.query_do_raw(c,
           'INSERT INTO %s (%s) VALUES (%s)' %
           (table, colnames, places),
           *[g.get(x[0]) for x in cols])
    return True
  except MySQLdb.IntegrityError:
    error("Dropping duplicate game '%s' from logfile '%s'"
                                  % (g.get('game_key'), g.get('source_file')))
    return False
  except:
    error("Failing query: " + c._last_executed)
    raise

def insert_games(c, g_list, table):
  cols = scload.LOG_DB_MAPPINGS
  colnames = scload.LOG_DB_SCOLUMNS
  places = scload.LOG_DB_SPLACEHOLDERS

  # TODO: handle NO_BUGGY_GAMES?
  try:
    c.executemany(
           'INSERT IGNORE INTO %s (%s) VALUES (%s)' % (table, colnames, places),
           [[g.get(x[0]) for x in cols] for g in g_list])
    return True
    # TODO: is there a way to detect duplicate keys on bulk insert?
  except:
    error("Failing query: " + c._last_executed)
    raise

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

def update_player_recent_games(c, g):
  player = g['name']
  if not (insert_game(c, g, 'player_recent_games')):
    return False
  if player_recent_game_count.has_key(player):
    player_recent_game_count.set_key(player_recent_game_count(c, player) + 1,
                                     player)
  if player_recent_game_count(c, player) > MAX_PLAYER_RECENT_GAMES + 50:
    extra = player_recent_game_count(c, player) - MAX_PLAYER_RECENT_GAMES
    ids = query_first_col(c, '''SELECT id FROM player_recent_games
                                 WHERE name = %s ORDER BY id LIMIT %s''',
                          player, extra)
    scload.delete_table_rows_by_id(c, 'player_recent_games', ids)
    player_recent_game_count.flush_key(player)
  return True

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
  global player_stats_cache, all_recent_games_cache
  winc = game_is_win(g) and 1 or 0

  if not update_player_recent_games(c, g):
    # game is a duplicate game - stop calculation here. This will only work if
    # duplicate games are read within a reasonable timeframe of each other...
    # but normally, they are adjacent in a logfile, or on a bulk read, loglines
    # will be sorted near each other.
    return False

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

  player_stats_cache.update(g)

  # Must be before player_last_game!
  update_player_streak(c, g)

  update_player_best_games(c, g)
  all_recent_games_cache.update(g)
  update_player_first_game(c, g)
  update_player_last_game(c, g)
  update_wins_table(c, g)
  return True

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

# subclasses of this object are designed to handle caching of information on
# the python side, for bulk INSERT into the database. The implementation of
# each is relatively idiosyncratic to the table and data, but they all follow
# the same schema: `update` caches the information, and `insert` performs an
# `executemany` call on a cursor.
class BulkDBCache(object):
  def __init__(self):
    pass

  def clear(self):
    """Clear the python-side data cache."""
    pass

  def update(self, g):
    """Update a python-side data cache with info from game g."""
    pass

  def insert(self, c):
    """Insert everything in the current cache into the database using cursor c."""
    pass

class AllRecentGames(BulkDBCache):
  def __init__(self):
    self.clear()

  def clear(self):
    self.games = list()

  def update(self, g):
    if is_junk_game(g):
      return
    if len(self.games) >= MAX_ALL_RECENT_GAMES:
      self.games.pop(0)
    self.games.append(g)

  def insert(self, c):
    # TODO: this goes once per commit, so that the db is in a
    # consistent state at each commit. But it could be even faster to do it
    # once per update cycle...
    if len(self.games) >= MAX_ALL_RECENT_GAMES:
      # on a bulk insert, we will be continually swapping these out -- no need
      # for subtlety. Note that this will wipe out ids entirely.
      c.execute("TRUNCATE TABLE all_recent_games")
      all_recent_game_count.set_key(MAX_ALL_RECENT_GAMES)
    else:
      extra = all_recent_game_count(c) + len(self.games) - MAX_ALL_RECENT_GAMES
      # old version first selected ids, then deleted by ids -- not sure if there
      # is any good reason for that?
      c.execute("DELETE FROM all_recent_games ORDER BY id LIMIT %d" % extra)
      if extra > 0:
        all_recent_game_count.set_key(MAX_ALL_RECENT_GAMES)
      else:
        all_recent_game_count.flush_key() # why do we even bother with this case?
    insert_games(c, self.games,'all_recent_games')
    dirty_page('recent', len(self.games))
    # TODO: why are these here and not with the per-day stats?
    dirty_page('per-day', len(self.games))
    dirty_page('per-day-monthly', len(self.games))
    self.clear()

class PlayerStats(BulkDBCache):
  def __init__(self):
    self.clear()

  def clear(self):
    # table players: dict key is lowercase name, value is a dict with the
    # field names
    self.players = dict()
    # table player_char_stats: dict key is lowercase name x charabbr, value
    # is a list of game count, max xl, win count
    self.pl_char = dict()

  def update(self, g):
    lname = g['name'].lower()
    winc = game_is_win(g) and 1 or 0
    if not self.pl_char.has_key((lname, g['charabbr'])):
      self.pl_char[(lname, g['charabbr'])] = [1, g['xl'], winc]
    else:
      d = self.pl_char[(lname, g['charabbr'])]
      d[0] += 1
      d[1] = max(d[1], g['xl'])
      d[2] += winc

    if not self.players.has_key(lname):
      self.players[lname] = {'name': g['name'],
                             'games_played': 1,
                             'games_won': winc,
                             'total_score': g['sc'],
                             'best_score': g['sc'],
                             'best_xl': g['xl'],
                             'first_game_start': g['start_time'],
                             'last_game_end': g['end_time'],
                             'max_runes': g['urune']}
    else:
      d = self.players[lname]
      d['games_played'] += 1
      d['games_won'] += winc
      d['total_score'] += g['sc']
      d['best_score'] = max(d['best_score'], g['sc'])
      d['best_xl'] = max(d['best_xl'], g['xl'])
      # WARNING: game start/end time assumes lines are read in order here...
      # TODO: drop this assumption?
      d['last_game_end'] = g['end_time']
      d['max_runes'] = max(d['max_runes'], g['urune'])

  def insert(self, c):
    players_l = [[self.players[k]['name'], # use case from logfile, not key
                  self.players[k]['games_played'],
                  self.players[k]['games_won'],
                  self.players[k]['total_score'],
                  self.players[k]['best_score'],
                  self.players[k]['best_xl'],
                  self.players[k]['first_game_start'],
                  self.players[k]['last_game_end'],
                  self.players[k]['max_runes']] for k in self.players.keys()]

    c.executemany('''INSERT INTO players
                             (name, games_played, games_won,
                              total_score, best_score, best_xl,
                              first_game_start, last_game_end, max_runes)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                      ON DUPLICATE KEY UPDATE
                             games_played = games_played + VALUES(games_played),
                             games_won = games_won + VALUES(games_won),
                             total_score = total_score + VALUES(total_score),
                             best_score = GREATEST(best_score, VALUES(best_score)),
                             best_xl = GREATEST(best_xl, VALUES(best_xl)),
                             max_runes = GREATEST(max_runes, VALUES(max_runes)),
                             last_game_end = VALUES(last_game_end),
                             current_combo = NULL''',
                  players_l)

    pl_char_l = [[k[0],
                  k[1],
                  self.pl_char[k][0],
                  self.pl_char[k][1],
                  self.pl_char[k][2]] for k in self.pl_char.keys()]
    c.executemany('''INSERT INTO player_char_stats
                             (name, charabbr, games_played, best_xl, wins)
                      VALUES (%s, %s, %s, %s, %s)
                      ON DUPLICATE KEY UPDATE
                          games_played = games_played + VALUES(games_played),
                          best_xl = GREATEST(best_xl, VALUES(best_xl)),
                          wins = wins + VALUES(wins)''',
                  pl_char_l)
    self.clear()

# handles two tables: per_day_stats and date_players
class PerDayStats(BulkDBCache):
  def __init__(self):
    self.clear()

  def clear(self):
    self.per_day_stats = dict()
    self.date_players = dict()

  def update(self, g):
    if is_junk_game(g):
      return

    # Grab just the date portion.
    edate = g['end_time'][:8]
    winc = game_is_win(g) and 1 or 0
    player = g['name']

    if not self.per_day_stats.has_key(edate):
      self.per_day_stats[edate] = [1, winc]
    else:
      self.per_day_stats[edate][0] += 1
      self.per_day_stats[edate][1] += winc

    if not self.date_players.has_key((edate, player)):
      self.date_players[(edate, player)] = [1, winc]
    else:
      self.date_players[(edate, player)][0] += 1
      self.date_players[(edate, player)][1] += winc

    # do the flush here because we are already working with the dates...
    # don't query these values until insert() has been called.
    # TODO: does it even make sense for these to be memoized?
    count_players_per_day.flush_key(edate)
    if winc:
      winners_for_day.flush_key(edate)

  def insert(self, c):
    # TODO: is there a faster way to do this without ON DUPLICATE KEY UPDATE?
    per_day_l = [[k,
                  self.per_day_stats[k][0],
                  self.per_day_stats[k][1]] for k in self.per_day_stats.keys()]

    c.executemany('''INSERT INTO per_day_stats (which_day, games_ended,
                                                games_won)
                                 VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                              games_ended = games_ended + VALUES(games_ended),
                              games_won = games_won + VALUES(games_won)''',
                  per_day_l)

    date_players_l = [[k[0],
                       k[0][:6],
                       k[1],
                       self.date_players[k][0],
                       self.date_players[k][1]] for k in self.date_players.keys()]
    c.executemany('''INSERT INTO date_players (which_day, which_month, player,
                                               games, wins)
                                 VALUES (%s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                         games = games + VALUES(games),
                                         wins = wins + VALUES(wins)''',
                date_players_l)
    # commit needs to happen elsewhere
    self.clear()

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
    query.db_races.flush()
    query.current_races.flush()
  if not is_known_class(c, cls):
    record_known_thing(c, 'known_classes', 'cls', cls)
    is_known_class.set_key(True, cls)
    query.db_classes.flush()
    query.current_classes.flush()

player_stats_cache = PlayerStats()
per_day_stats_cache = PerDayStats()
all_recent_games_cache = AllRecentGames()

def act_on_logfile_line(c, this_game):
  """Actually assign things and write to the db based on a logfile line
  coming through. All lines get written to the db; some will assign
  irrevocable points and those should be assigned immediately. Revocable
  points (high scores, lowest dungeon level, fastest wins) should be
  calculated elsewhere."""

  if 'start_time' not in this_game:
    return

  # Update statistics for this player's game.
  if update_player_stats(c, this_game):
    update_topN(c, this_game, TOP_N)
    update_combo_scores(c, this_game)
    update_killer_stats(c, this_game)
    update_gkills(c, this_game)
    per_day_stats_cache.update(this_game)
    update_known_races_classes(c, this_game)

def periodic_flush(c):
  player_stats_cache.insert(c)
  per_day_stats_cache.insert(c)
  all_recent_games_cache.insert(c)
