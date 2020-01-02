#!/usr/bin/python
try:
  import MySQLdb
except ImportError:
  import pymysql as MySQLdb

import scload
import query

import logging
from logging import debug, info, warn, error
import crawl_utils
from memoizer import DBMemoizer
import crawl

from scload import query_do, query_first, query_first_col, wrap_transaction
from scload import query_first_def, game_is_win, query_row, query_rows
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

def game_is_buggy(g):
  return g.get('game_key') in scload.BUGGY_GAMES

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
  if table in NO_BUGGY_GAMES and game_is_buggy(g):
    info('Ignoring buggy game %s for %s', g.get('game_key'), table)
    return False
  try:
    scload.query_do_raw(c,
           'INSERT INTO %s (%s) VALUES (%s)' %
           (table, colnames, places),
           *[g.get(x[0]) for x in cols])
    return True
  except MySQLdb.IntegrityError:
    error("insert_game: ignoring duplicate game '%s' from logfile '%s'"
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

# TODO: does TOP_N really need to be 1000? does anyone ever even look at that
# leaderboard?
# However, this is really only heavy towards the beginning of loading data
# during a bulk import, so there may not be a need to optimize it further.
def update_topN(c, g, n):
  if topN_count(c) >= n:
    if g['sc'] > lowest_highscore(c):
      # note: for some reason this particular query is faster than just a simple
      # DELETE FROM ... ORDER BY query.
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

def player_active_streak_id(c, player):
  return query_first(c, '''SELECT id FROM streaks
                                    WHERE player = %s AND active = 1''',
                     player)

# not much point in memoizing this one. See
# `player_recent_cache.game_key_exists` for something that will be much more
# efficient during bulk loads.
def game_key_in_db(c, g):
  # check just two tables: player_recent_games and wins. This could result
  # in some duplicates being added, but I'm not sure if the trouble here is
  # worth it -- because the db doesn't store all games, it relies on (to some
  # degree) reading games in order no matter what.
  n = query_first(c, '''SELECT count(game_key) FROM player_recent_games
                                        WHERE game_key = %s''', g['game_key'])
  if n > 0:
    return True
  n = query_first(c, '''SELECT count(game_key) FROM wins
                                        WHERE game_key = %s''', g['game_key'])
  return n > 0

def update_player_first_game(c, g):
  player = g['name']
  if not player_first_game_exists(c, player):
    player_first_game_exists.flush_key(player)
    insert_game(c, g, 'player_first_games')

def update_player_stats(c, g):
  global player_stats_cache, all_recent_games_cache, streaks_cache
  global player_recent_cache, player_best_cache, wins_cache
  winc = game_is_win(g) and 1 or 0

  if player_recent_cache.game_key_exists(c, g):
    error("Ignoring duplicate game '%s' from logfile '%s'"
                                  % (g.get('game_key'), g.get('source_file')))
    return False

  player_recent_cache.update(g)

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

  streaks_cache.init_from_db(c) # TODO: could do this somewhere else
  streaks_cache.update(g)

  player_best_cache.update(g)
  all_recent_games_cache.update(g)
  wins_cache.update(g)
  update_player_first_game(c, g)
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
    fn.set_key(sc, value)
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

class Wins(BulkDBCache):
  def __init__(self):
    self.clear()

  def clear(self):
    self.games = list()

  def update(self, g):
    if not game_is_win(g) or game_is_buggy(g):
      return
    dirty_pages('winners', 'fastest-wins-turns', 'fastest-wins-time',
            'overview')
    self.games.append(g)

  def insert(self, c):
    insert_games(c, self.games, 'wins')
    self.clear()

class PlayerBestGames(BulkDBCache):
  def __init__(self):
    self.clear()

  def clear(self):
    self.games = dict() # player -> game list

  def update(self, g):
    # TODO: is it better to do the real score check here or in insert?
    lname = g['name'].lower()
    score = g['sc']
    if not self.games.has_key(lname):
      self.games[lname] = [g]
    elif score > self.games[lname][0]['sc']:
      i = 1
      while (i < len(self.games[lname])):
        if score > self.games[lname][i]['sc']:
          break
        i += 1
      self.games[lname].insert(i, g)
      if len(self.games[lname]) > MAX_PLAYER_BEST_GAMES:
        self.games[lname].pop(0)

  def insert(self, c):
    del_l = list()
    ins_l = list()
    for n in self.games.keys():
      pgames = self.games[n]
      gamecount = player_best_game_count(c, n)

      # first fill up the list to the max with the highest scoring games we
      # have
      while len(pgames) and gamecount < MAX_PLAYER_BEST_GAMES:
        g = pgames.pop()
        ins_l.append(g)
        if g['sc'] < player_lowest_highscore(c, n):
          player_lowest_highscore.set_key(g['sc'], n)
        gamecount += 1

      # now we do any high scores that are actually high enough.
      flush_lowest = False
      while len(pgames):
        g = pgames.pop()
        # heuristic: just see if they meet a minimum threshold, and then delete
        # later. Otherwise, we need to do a db call each time.
        if g['sc'] > player_lowest_highscore(c, n):
          ins_l.append(g)
          # TODO: handle max insertion case? can just check the lowest of the
          # inserted games
          flush_lowest = True
          gamecount += 1
        else:
          break # pgames is sorted

      extras = 0
      if gamecount > MAX_PLAYER_BEST_GAMES:
        # delete any excess
        extras = gamecount - MAX_PLAYER_BEST_GAMES
        del_l.append((n, gamecount - MAX_PLAYER_BEST_GAMES))
        gamecount = MAX_PLAYER_BEST_GAMES

      player_best_game_count.set_key(gamecount, n)
      if flush_lowest:
        player_lowest_highscore.flush_key(n)

    # do the insertion first, because the imprecise way that high-scoring games
    # are handled may involve some of the inserted games being deleted
    insert_games(c, ins_l, 'player_best_games')
    c.executemany('''DELETE FROM player_best_games WHERE name=%s
                            ORDER BY sc LIMIT %s''', del_l)
    self.clear()

# This class tracks most recent games, and also handles duplicate checking. It
# has somewhat complicated differential behavior depending on whether the db
# started empty: if it did start empty, the assumption is that games will
# be read enough in order that duplicate checking can rely entirely on a
# python-side caching of the most recent n gids. To complicate things, games
# are read by their end_time, not start_time. There are two cases to worry
# about:
# (i) identical game records. These are handled just fine, because they have
#     the same end_time as well as start_time.
# (ii) duplicate game_keys generated because a game crashed after a logline
#      was written, but before the save was deleted. This should only be
#      possible in old versions of dcss, and most of the cases I know of are
#      handled by the heuristic cache size I have selected here.
#      HOWEVER, if the player then takes a very long time to complete the
#      game in a case like this, the optimized version of the game_key check
#      will not catch it. If the heuristic misses a case, the game will still
#      run up against the unique constraint on the two key tables (which is
#      handled via INSERT IGNORE).
#      (Side note: it's sort of unclear what to even do with these game
#      records. Sequell allows duplicate game keys for this case...)
#
# The reason for this perhaps excessive-seeming optimization is that duplicate
# checking is the heaviest remaining db access in the logline processing loop
# without it.
class PlayerRecentGames(BulkDBCache):
  def __init__(self):
    self.most_recent_start = None # string in morgue start_time format
    self.empty_db_gid_cache = set()
    self.empty_db_gid_cache_l = list()
    self.EMPTY_DB_CACHE_SIZE = 1000
    self.empty_db_start = False
    self.clear()

  def past_most_recent(self, g):
    if self.most_recent_start is None:
      return True # requires that initialization from db precede any calls to this

    # morgue start_time is YMDHMS order, so simple lexicographic comparison
    # works.
    return g['start_time'] > self.most_recent_start

  def init_most_recent_from_db(self, c):
    import morgue.time
    db_time = query_first(c,
                          '''SELECT MAX(start_time) FROM all_recent_games''')
    if db_time is None:
      self.most_recent_start = None
      self.empty_db_start = True
    else:
      self.most_recent_start = morgue.time.morgue_timestring(db_time)

  def _game_key_in_db_or_cache(self, c, g):
    if self.empty_db_start:
      return g['game_key'] in self.empty_db_gid_cache
    else:
      return game_key_in_db(c, g) # fall back to a SELECT query

  def game_key_exists(self, c, g):
    """Check whether a game key exists in the db."""
    if self.most_recent_start is None:
      self.init_most_recent_from_db(c)
    # since game_key includes start time, a game that is more recent than any
    # we've seen can't be a duplicate.
    if self.past_most_recent(g):
      return False
    if g['game_key'] in self.gids:
      return True
    return self._game_key_in_db_or_cache(c, g)

  def update(self, g):
    if self.past_most_recent(g):
      self.most_recent_start = g['start_time']
    if self.empty_db_start:
      if len(self.empty_db_gid_cache_l) > self.EMPTY_DB_CACHE_SIZE:
        self.empty_db_gid_cache.remove(self.empty_db_gid_cache_l.pop(0))
      self.empty_db_gid_cache_l.append(g['game_key'])
      self.empty_db_gid_cache.add(g['game_key'])
    lname = g['name'].lower()
    if not self.games.has_key(lname):
      self.games[lname] = list()
    self.games[lname].append(g)
    if len(self.games[lname]) > MAX_PLAYER_RECENT_GAMES:
      self.games[lname].pop(0)
    self.gids.add(g['game_key'])

  def insert(self, c):
    # TODO: not sure this call will work very well
    player_recent_count = {n: player_recent_game_count(c, n)
                      for n in self.games.keys()
                      if len(self.games[n]) < MAX_PLAYER_RECENT_GAMES}
    del_l = list() # how many recent games to cull for each player
    games_l = list() # games to insert
    for n in self.games.keys():
      games_l.extend(self.games[n])
      if len(self.games[n]) >= MAX_PLAYER_RECENT_GAMES:
        # delete anything that's there, we will replace it all
        del_l.append((n, MAX_PLAYER_RECENT_GAMES))
        player_recent_game_count.set_key(MAX_PLAYER_RECENT_GAMES, n)
      else:
        extras = max(0, player_recent_count[n] + len(self.games[n])
                                                  - MAX_PLAYER_RECENT_GAMES)
        if extras > 0:
          del_l.append((n, extras))
        player_recent_game_count.set_key(min(player_recent_count[n]
                                                  + len(self.games[n]),
                                                  MAX_PLAYER_RECENT_GAMES), n)
    c.executemany('''DELETE FROM player_recent_games WHERE name=%s
                            ORDER BY id LIMIT %s''', del_l)
    insert_games(c, games_l, 'player_recent_games')
    self.clear()

  def clear(self):
    # don't clear most recent start -- it should be always up-to-date.
    self.games = dict() # player -> game list
    self.gids = set()

class KillerStats(BulkDBCache):
  def __init__(self):
    self.clear()

  def clear(self):
    self.killer_stats = dict() # ckiller -> count, recent game

  def update(self, g):
    ckiller = g['ckiller']
    if self.killer_stats.has_key(ckiller):
      self.killer_stats[ckiller] = (self.killer_stats[ckiller][0] + 1, g)
    else:
      self.killer_stats[ckiller] = (1, g)

  def insert(self, c):
    dirty_page('killers', len(self.killer_stats))
    killcounts_l = [(k,
                     self.killer_stats[k][0],
                     self.killer_stats[k][1]['name'])
                                        for k in self.killer_stats.keys()]
    c.executemany('''INSERT INTO top_killers
                             (ckiller, kills, most_recent_victim)
                     VALUES (%s, %s, %s)
                     ON DUPLICATE KEY UPDATE
                          kills = kills + VALUES(kills),
                          most_recent_victim = VALUES(most_recent_victim)''',
                  killcounts_l)

    killgames_del = [(ckiller,) for ckiller in self.killer_stats.keys()]
    killgames_ins = [self.killer_stats[k][1] for k in self.killer_stats.keys()]
    c.executemany('''DELETE FROM killer_recent_kills WHERE ckiller = %s''',
                  killgames_del)
    insert_games(c, killgames_ins, 'killer_recent_kills')
    self.clear()

# data structure for tracking individual streaks -- handles both streaks in the
# db, and streaks that entirely consist of recently observed games.
class StreakMod(object):
  def __init__(self, player, db_id, follows_known_loss):
    self.active = True
    self.player = player
    self.db_id = db_id
    self.games = list()
    self.continues_db = db_id is not None
    self.follows_known_loss = follows_known_loss

  def add_game(self, g):
    self.games.append(g)
    if not game_is_win(g):
      self.active = False
    return self.active

  def min_known_len(self):
    known_db_games = self.continues_db and 1 or 0
    last_game_loss = (not self.active) and 1 or 0
    # note: follows_known_loss doesn't actually impact this, because it doesn't
    # affect the *minimum* length
    return len(self.games) + known_db_games - last_game_loss

# handle all streak-related tables, as well as player_last_game.
# unlike many other subclasses of BulkDBCache, this is designed to continually
# have accurate tracking of active streaks. It needs to be initialized from
# the db before doing any processing.
# TODO: this might be a lot simpler if the db stored any loss following a win
# as a potential streak-breaker, and then reconstructed the >1-streaks from
# there, rather than trying to caclulate it all ahead of time on import...
# or even just stored open 1-streaks, though this would make the table size
# balloon.
class Streaks(BulkDBCache):
  def __init__(self):
    self.clear()
    self.db_streaks = None

  def update_db_streaks(self, c):
    # in the full cao db, this is usually around 100 streaks at any given time
    self.db_streaks = dict()
    s = query_rows(c, 'SELECT LOWER(player), id FROM streaks WHERE active = 1')
    if s:
      self.db_streaks.update(s)

  def init_from_db(self, c):
    if self.db_streaks is None:
      self.update_db_streaks(c)

  def ongoing_streak(self, name):
    ln = name.lower()
    if self.cached_streaks.has_key(ln):
      return True
    if ln in self.cached_closed_streak_players:
      return False
    return self.db_streaks.has_key(ln)

  def streak_to_continue(self, lname):
    if self.cached_streaks.has_key(lname):
      streak_to_continue = self.cached_streaks[lname]
    else:
      # the case where the cached game in last_games is a win should already
      # be taken care of by an existing StreakMod.
      if lname in self.cached_closed_streak_players:
        sid = None # if they have no cached streaks, and a closed cached streak,
                   # then definitely do not connect do a db streak
        last_lost = True
      else:
        # n.b. a db streak that is closed by a game we have seen recently will
        # ensure that there is a cached closed streak
        sid = self.db_streaks.get(lname) # may be None
        last_lost = self.last_games.has_key(lname)
      streak_to_continue = StreakMod(lname, sid, last_lost)
    return streak_to_continue

  def update(self, g):
    if game_is_buggy(g):
      return
    # at this point we treat 1-game win sequences as potential streaks, and
    # create a streak entry for them. When inserting into the db, we will
    # actually check whether they follow a win. # TODO: this could be better
    lname = g['name'].lower()
    if game_is_win(g) or self.ongoing_streak(lname):
      streak = self.streak_to_continue(lname)
      if streak.add_game(g): # active streak
        self.cached_streaks[lname] = streak
        #info("    Adding %s to active streak %s, length %d", g['game_key'], repr(streak.db_id), len(streak.games))
      else: # inactivate streak
        if self.cached_streaks.has_key(lname):
          del self.cached_streaks[lname]
        if streak.min_known_len() > 1 or not streak.follows_known_loss:
          #info("Closing streak for %s", g['name'])
          self.cached_closed_streaks.append(streak)
          self.cached_closed_streak_players.add(lname)
        #else:
        #  info("Dropping 1-streak for %s", g['name'])

    self.last_games[lname] = g

  # for when the last game was a win, and is not cached. We will need to first
  # set up the streak, then add the uncached win to streak_games.
  def _player_create_streak_from_last(self, c, player):
    end_time = player_last_game_end_time(c, player)
    query_do(c, '''INSERT INTO streaks
                               (player, start_game_time, end_game_time,
                                active, ngames)
                        VALUES (%s, %s, %s, %s, %s)''',
             player, end_time, end_time,
             True, 1)

    # Record the game that started the streak:
    query_do(c,
             "INSERT INTO streak_games (" + scload.LOG_DB_SCOLUMNS + ") " +
             "SELECT " + scload.LOG_DB_SCOLUMNS +
             ''' FROM player_last_games WHERE name = %s''', player)

    sid = query_first(c, '''SELECT id FROM streaks
                                      WHERE player = %s AND active = 1''',
                         player)
    if self.db_streaks.has_key(player):
      error("Player %s already has an ongoing streak!" % player)
    # return the newly-created streak id
    self.db_streaks[player] = sid
    return sid

  # for when the last game was not a win, and g begins the streak
  # *does not* insert g, just uses it for setting times
  def _player_create_streak_from_first(self, c, player, g):
    query_do(c, '''INSERT INTO streaks
                               (player, start_game_time, end_game_time,
                                active, ngames)
                        VALUES (%s, %s, %s, %s, %s)''',
             player, g['end_time'], g['end_time'],
             True, 0)
    sid = query_first(c, '''SELECT id FROM streaks
                                      WHERE player = %s AND active = 1''',
                       player)
    if self.db_streaks.has_key(player):
      error("Player %s already has an ongoing streak!" % player)
    self.db_streaks[player] = sid
    # return the newly-created streak id
    return sid

  def _player_break_streak(self, c, player, g, sid):
    query_do(c, '''UPDATE streaks SET active = 0 WHERE id = %s''', sid)
    g['streak_id'] = sid
    insert_game(c, g, 'streak_breakers', extras = ['streak_id'])
    if self.db_streaks.has_key(player):
      del self.db_streaks[player]

  def _player_extend_streak(self, c, player, g):
    query_do(c, '''UPDATE streaks SET end_game_time = %s, ngames = ngames + 1
                                WHERE player = %s AND active = 1''',
             g['end_time'], player)
    insert_game(c, g, 'streak_games')

  def _db_continue_streak(self, c, player, g, sid):
    if game_is_win(g):
      self._player_extend_streak(c, player, g)
    else:
      self._player_break_streak(c, player, g, sid)

  def insert(self, c):
    # it's important to close out streaks first, in case a player begins new
    # ones. Order of ongoing streaks is not preserved here, but that should
    # be ok...
    cached_streaks = [s for s in self.cached_closed_streaks]
    cached_streaks.extend(self.cached_streaks.values())

    # Deal with any 1-streaks that are waiting for a db check about whether
    # they follow a loss or a win. First, we do the db checks so that False for
    # follows_known_loss means it follows a db win.
    for s in cached_streaks:
      if not s.follows_known_loss:
        s.follows_known_loss = not player_won_last_game(c, s.player) # possible db access
    confirmed_streaks = [s for s in cached_streaks
                           if s.min_known_len() > 1
                              or not s.follows_known_loss]

    # now everything is a >1-streak. However, we may need to connect up either
    # with an existing streak in the db, or a preceding win that is not in the
    # cache.

    for s in confirmed_streaks:
      # handle initial game
      if s.db_id is not None:
        sid = s.db_id
        #info("db: adding to streak %d" % s.db_id)
      elif s.follows_known_loss:
        sid = self._player_create_streak_from_first(c, s.player, s.games[0])
        #info("db: creating new streak %d from %s" % (sid, s.games[0]['game_key']))
      else:
        # this takes care of the game in the db
        sid = self._player_create_streak_from_last(c, s.player)
        #info("db: creating new streak %d from db game" % sid)

      for g in s.games:
        self._db_continue_streak(c, s.player, g, sid)
        #info("    inserting game %s" % g['game_key'])

    # finally, update player_last_games in the db
    last_games_del = [[name] for name in self.last_games.keys()]
    last_games_ins = [self.last_games[name] for name in self.last_games.keys()]

    c.executemany('''DELETE FROM player_last_games WHERE name=%s''',
                  last_games_del)
    insert_games(c, last_games_ins, 'player_last_games')

    self.clear()

  def clear(self):
    self.cached_streaks = dict() # player -> StreakMod
    self.cached_closed_streaks = list() # list of StreakMods
    self.cached_closed_streak_players = set() # set of names
    self.last_games = dict() # player -> game

class AllRecentGames(BulkDBCache):
  def __init__(self):
    self.clear()

  def clear(self):
    self.games = list()

  def update(self, g):
    if is_junk_game(g) or game_is_buggy(g):
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
      if extra > 0:
        c.execute("DELETE FROM all_recent_games ORDER BY id LIMIT %d" % extra)
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

player_recent_cache = PlayerRecentGames()
player_stats_cache = PlayerStats()
player_best_cache = PlayerBestGames()
per_day_stats_cache = PerDayStats()
all_recent_games_cache = AllRecentGames()
killer_stats_cache = KillerStats()
streaks_cache = Streaks()
wins_cache = Wins()

def act_on_logfile_line(c, this_game):
  """Actually assign things and write to the db based on a logfile line
  coming through. All lines get written to the db; some will assign
  irrevocable points and those should be assigned immediately. Revocable
  points (high scores, lowest dungeon level, fastest wins) should be
  calculated elsewhere."""

  global killer_stats_cache, per_day_stats_cache

  if 'start_time' not in this_game:
    return

  # Update statistics for this player's game.
  if update_player_stats(c, this_game):
    update_topN(c, this_game, TOP_N)
    update_combo_scores(c, this_game)
    killer_stats_cache.update(this_game)
    update_gkills(c, this_game)
    per_day_stats_cache.update(this_game)
    update_known_races_classes(c, this_game)

def periodic_flush(c):
  global streaks_cache, player_stats_cache, per_day_stats_cache
  global all_recent_games_cache, killer_stats_cache, player_recent_cache
  global player_best_cache, wins_cache
  streaks_cache.insert(c)
  player_recent_cache.insert(c)
  player_best_cache.insert(c)
  player_stats_cache.insert(c)
  per_day_stats_cache.insert(c)
  all_recent_games_cache.insert(c)
  killer_stats_cache.insert(c)
  wins_cache.insert(c)
