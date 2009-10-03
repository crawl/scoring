#!/usr/bin/python

import loaddb
import query
import banner

import logging
from logging import debug, info, warn, error
import crawl_utils
from crawl_utils import DBMemoizer
import crawl
import uniq

from loaddb import query_do, query_first, query_first_col, wrap_transaction
from loaddb import query_first_def, game_is_win

import nemchoice

TOP_N = 1000
MAX_PLAYER_BEST_GAMES = 15
MAX_PLAYER_RECENT_GAMES = 15
MAX_ALL_RECENT_GAMES = 100

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

class OutlineListener (loaddb.CrawlEventListener):
  def logfile_event(self, cursor, logdict):
    act_on_logfile_line(cursor, logdict)

  def milestone_event(self, cursor, milestone):
    act_on_milestone(cursor, milestone)

  def cleanup(self, db):
    cursor = db.cursor()
    try:
      pass
      #update_player_scores(cursor)
    finally:
      cursor.close()

class OutlineTimer (loaddb.CrawlTimerListener):
  def run(self, cursor, elapsed):
    update_player_scores(cursor)

LISTENER = [ OutlineListener() ]

# Update player scores every so often.
TIMER = [ ( crawl_utils.UPDATE_INTERVAL, OutlineTimer() ) ]

def act_on_milestone(c, this_mile):
  """This function takes a milestone line, which is a string composed of key/
  value pairs separated by colons, and parses it into a dictionary.
  Then, depending on what type of milestone it is (key "type"), another
  function may be called to finish the job on the milestone line. Milestones
  have the same broken :: behavior as logfile lines, yay."""
  pass

@DBMemoizer
def topN_count(c):
  return query_first(c, '''SELECT COUNT(*) FROM top_games''')

@DBMemoizer
def lowest_highscore(c):
  return query_first(c, '''SELECT MIN(sc) FROM top_games''')

def insert_game(c, g, table, extras = []):
  cols = loaddb.LOG_DB_MAPPINGS
  if extras:
    cols = list(cols)
    for item in extras:
      cols.append([item, item])
  query_do(c,
           'INSERT INTO %s (%s) VALUES (%s)' %
           (table, ",".join([x[1] for x in cols]),
            ",".join(["%s" for x in cols])),
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
  else:
    insert_game(c, g, 'top_games')
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
           "INSERT INTO streak_games (" + loaddb.LOG_DB_SCOLUMNS + ") " +
           "SELECT " + loaddb.LOG_DB_SCOLUMNS +
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
  else:
    if player_streak_is_active(c, player):
      player_extend_streak(c, player, g)
    elif player_won_last_game(c, player):
      player_create_streak(c, player, g)
      player_streak_is_active.flush_key(player)

def update_all_recent_games(c, g):
  if all_recent_game_count(c) >= MAX_PLAYER_RECENT_GAMES:
    query_do(c, '''DELETE FROM all_recent_games WHERE id = %s''',
             query_first(c, '''SELECT id FROM all_recent_games
                                     ORDER BY id LIMIT 1'''))
  else:
    all_recent_game_count.flush()
  insert_game(c, g, 'all_recent_games')

def update_player_recent_games(c, g):
  player = g['name']
  if player_recent_game_count(c, player) >= MAX_PLAYER_RECENT_GAMES:
    query_do(c, '''DELETE FROM player_recent_games WHERE id = %s''',
             query_first(c, '''SELECT id FROM player_recent_games
                                        WHERE name = %s ORDER BY id LIMIT 1''',
                         player))
  else:
    player_recent_game_count.flush_key(c, player)
  insert_game(c, g, 'player_recent_games')

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
    insert_game(c, g, 'wins')

def update_player_stats(c, g):
  winc = game_is_win(g) and 1 or 0
  query_do(c, '''INSERT INTO players
                             (name, games_played, games_won,
                              total_score, best_score, best_xl,
                              first_game_start, last_game_end)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
                             last_game_end = %s,
                             current_combo = NULL''',
           g['name'], 1, winc, g['sc'], g['sc'], g['xl'], g['start_time'],
           g['end_time'],
           winc, g['sc'], g['sc'], g['sc'], g['xl'], g['xl'], g['end_time'])

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

def update_combo_scores(c, g):
  update_topscore_table_for(c, g, top_score_for_combo,
                            'top_combo_scores', 'charabbr')
  update_topscore_table_for(c, g, top_score_for_species,
                            'top_species_scores', 'raceabbr')
  update_topscore_table_for(c, g, top_score_for_class,
                            'top_class_scores', 'cls')

def act_on_logfile_line(c, this_game):
  """Actually assign things and write to the db based on a logfile line
  coming through. All lines get written to the db; some will assign
  irrevocable points and those should be assigned immediately. Revocable
  points (high scores, lowest dungeon level, fastest wins) should be
  calculated elsewhere."""

  # Update top-1000.
  update_topN(c, this_game, TOP_N)

  # Update statistics for this player's game.
  update_player_stats(c, this_game)

  update_combo_scores(c, this_game)
