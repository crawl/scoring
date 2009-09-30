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

import nemchoice

TOP_N = 1000

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

def insert_game(c, g, table):
  query_do(c,
           'INSERT INTO %s (%s) VALUES (%s)' %
           (table, loaddb.LOG_DB_SCOLUMNS, loaddb.LOG_DB_SPLACEHOLDERS),
           *[g.get(x[1]) for x in loaddb.LOG_DB_MAPPINGS])

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

def game_is_win(g):
  return g['ktyp'] == 'winning'

def update_player_stats(c, g):
  winc = game_is_win(g) and 1 or 0
  query_do(c, '''INSERT INTO players
                             (name, games_played, games_won,
                              total_score, best_score,
                              first_game_start, last_game_end)
                      VALUES (%s, %s, %s, %s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE
                             games_played = games_played + 1,
                             games_won = games_won + %s,
                             total_score = total_score + %s,
                             best_score =
                                   CASE WHEN best_score < %s
                                        THEN %s
                                        ELSE best_score
                                        END,
                             last_game_end = %s,
                             current_combo = NULL''',
           g['name'], 1, winc, g['sc'], g['sc'], g['start_time'],
           g['end_time'],
           winc, g['sc'], g['sc'], g['sc'], g['end_time'])

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
