# Library to query the database and update scoring information. Raw data entry
# from logfile and milestones is done in loaddb.py, this is for queries and
# post-processing.

import logging
from logging import debug, info, warn, error

import loaddb
from loaddb import Query, query_do, query_first, query_row, query_rows
from loaddb import query_first_col, query_first_def

import crawl
import crawl_utils
from crawl_utils import DBMemoizer, morgue_link, linked_text, human_number
import uniq
import os.path
import re
from datetime import datetime
import time

# Number of unique uniques
MAX_UNIQUES = 43
MAX_RUNES = 15

def _cursor():
  """Easy retrieve of cursor to make interactive testing easier."""
  d = loaddb.connect_db()
  return d.cursor()

def _filter_invalid_where(d):
  if loaddb.is_not_tourney(d):
    return None
  status = d['status']
  if status in [ 'quit', 'won', 'bailed out', 'dead' ]:
    return None
  else:
    d['status'] = status.title() or 'Active'
    return d

def time_from_str(when):
  if isinstance(when, datetime):
    return when
  if when.endswith('D') or when.endswith('S'):
    when = when[:-1]
  return datetime(*(time.strptime(when, '%Y%m%d%H%M%S')[0:6]))

def canonical_where_name(name):
  test = '%s/%s' % (crawl_utils.RAWDATA_PATH, name)
  if os.path.exists(test):
    return name
  names = os.listdir(crawl_utils.RAWDATA_PATH)
  names = [ x for x in names if x.lower() == name.lower() ]
  if names:
    return names[0]
  else:
    return None

def whereis_player(name):
  name = canonical_where_name(name)
  if name is None:
    return name

  where_path = '%s/%s/%s.where' % (crawl_utils.RAWDATA_PATH, name, name)
  if not os.path.exists(where_path):
    return None

  try:
    f = open(where_path)
    try:
      line = f.readline()
      d = loaddb.apply_dbtypes( loaddb.xlog_dict(line) )
      return _filter_invalid_where(d)
    finally:
      f.close()
  except:
    return None

def row_to_xdict(row):
  return dict( zip(loaddb.LOG_DB_COLUMNS, row) )

def xdict_rows(rows):
  return [row_to_xdict(x) for x in rows]

@DBMemoizer
def canonicalize_player_name(c, player):
  row = query_row(c, '''SELECT name FROM players WHERE name = %s''',
                  player)
  if row:
    return row[0]
  return None

def find_games(c, table, sort_min=None, sort_max=None,
               limit=None, **dictionary):
  """Finds all games matching the supplied criteria, all criteria ANDed
  together."""

  if sort_min is None and sort_max is None:
    sort_min = 'end_time'

  query = Query('SELECT ' + loaddb.LOG_DB_SCOLUMNS + (' FROM %s' % table))
  where = []
  values = []

  def append_where(where, clause, *newvalues):
    where.append(clause)
    for v in newvalues:
      values.append(v)

  for key, value in dictionary.items():
    if key == 'before':
      append_where(where, "end_time < %s", value)
    else:
      append_where(where, key + " = %s", value)

  order_by = ''
  if sort_min:
    order_by += ' ORDER BY ' + sort_min
  elif sort_max:
    order_by += ' ORDER BY ' + sort_max + ' DESC'

  if where:
    query.append(' WHERE ' + ' AND '.join(where), *values)

  if order_by:
    query.append(order_by)

  if limit:
    query.append(' LIMIT %d' % limit)

  return [ row_to_xdict(x) for x in query.rows(c) ]

def calc_perc(num, den):
  if den <= 0:
    return 0.0
  else:
    return num * 100.0 / den

def calc_perc_pretty(num, den):
  return "%.2f" % calc_perc(num, den)

def find_place(rows, player):
  """Given a list of one-tuple rows, returns the index at which the given
  player name occurs in the one-tuples, or -1 if the player name is not
  present in the list."""
  if rows is None:
    return -1
  p = [r[0] for r in rows]
  if player in p:
    return p.index(player)
  else:
    return -1

def do_place_numeric(rows, callfn):
  index = -1
  last_num = None
  for r in rows:
    if last_num != r[1]:
      index += 1
    last_num = r[1]
    if not callfn(r, index):
      break

def find_place_numeric(rows, player):
  """Given a list of two-tuple rows, returns the index at which the given
  player name occurs in the two-tuples, or -1 if the player name is not
  present in the list. The second element of each tuple is considered to be
  a score. If any element has the same score as a preceding element, it is
  treated as being at the same index."""
  index = -1
  last_num = None
  for r in rows:
    if last_num != r[1]:
      index += 1
    last_num = r[1]
    if r[0] == player:
      return index
  return -1

def player_best_game(c, player):
  return (row_to_xdict(
      query_row(c, 'SELECT ' + loaddb.LOG_DB_SCOLUMNS
                + ''' FROM player_best_games WHERE name = %s
                     ORDER BY sc DESC LIMIT 1''',
                player)))

def player_first_game(c, player):
  return (row_to_xdict(
      query_row(c, 'SELECT ' + loaddb.LOG_DB_SCOLUMNS
                + ''' FROM player_first_games WHERE name = %s''',
                player)))

def player_last_game(c, player):
  return (row_to_xdict(
      query_row(c, 'SELECT ' + loaddb.LOG_DB_SCOLUMNS
                + ''' FROM player_last_games WHERE name = %s''',
                player)))

def calc_avg_int(num, den):
  if den == 0:
    return 0
  else:
    return int(num / den)

def game_select_from(table):
  return "SELECT " + loaddb.LOG_DB_SCOLUMNS + " FROM " + table + " "

def player_best_first_last(c, player):
  fields = loaddb.LOG_DB_SCOLUMNS
  q = [(game_select_from('player_best_games') +
        '''WHERE name = %s ORDER BY sc DESC LIMIT 1'''),
       (game_select_from('player_first_games') +
        '''WHERE name = %s'''),
       (game_select_from('player_last_games') +
        '''WHERE name = %s''')]
  q = " UNION ALL ".join(["(" + x + ")" for x in q])
  return xdict_rows(query_rows(c, q, player, player, player))

def best_players_by_total_score(c):
  rows = query_rows(c, '''SELECT name, games_played, games_won,
                                 total_score, best_score,
                                 first_game_start, last_game_end
                            FROM players
                          ORDER BY total_score DESC''')
  res = []
  for r in rows:
    rl = list(r)
    games = player_best_first_last(c, rl[0])
    rl[4] = linked_text(games[0], morgue_link, human_number(rl[4]))
    rl[5] = linked_text(games[1], morgue_link, rl[5])
    rl[6] = linked_text(games[2], morgue_link, rl[6])
    win_perc = calc_perc_pretty(rl[2], rl[1]) + "%"
    avg_score = calc_avg_int(rl[3], rl[1])
    res.append([rl[3]] + list(rl[0:3]) + [win_perc] + [rl[4]]
               + [avg_score] + list(rl[5:]))
  return res

def all_player_stats(c):
  rows = query_rows(c, '''SELECT name, games_played, games_won,
                                 total_score, best_xl, best_score,
                                 first_game_start, last_game_end
                            FROM players
                           ORDER BY name''')
  res = []
  for r in rows:
    rl = list(r)
    games = player_best_first_last(c, rl[0])
    rl[5] = linked_text(games[0], morgue_link, human_number(rl[5]))
    rl[6] = linked_text(games[1], morgue_link, rl[6])
    rl[7] = linked_text(games[2], morgue_link, rl[7])
    win_perc = calc_perc_pretty(rl[2], rl[1]) + "%"
    avg_score = calc_avg_int(rl[3], rl[1])
    res.append([rl[3]] + list(rl[0:3]) + [win_perc] + rl[4:6]
               + [avg_score] + list(rl[6:]))
  return res

def top_combo_scores(c):
  """Returns all the top-scoring games for each unique character combo, ordered
in descending order of score."""
  rows = query_rows(c,
                    game_select_from('top_combo_scores') +
                    " ORDER BY sc DESC")
  return xdict_rows(rows)

def select_fields(*fields):
  return lambda g: [g.get(x) for x in fields]

def top_thing_scorers(c, table, thing):
  games = xdict_rows(query_rows(c, game_select_from(table)
                                + " ORDER BY name, " + thing))
  score_counts = { }

  def inc_count(g):
    name = g['name']
    if not score_counts.has_key(name):
      score_counts[name] = [ ]
    l = score_counts[name]
    l.append(linked_text(g, morgue_link, g[thing]))

  for g in games:
    inc_count(g)

  best_players = score_counts.items()
  best_players.sort(lambda a, b: len(b[1]) - len(a[1]))
  return [[len(x[1]), x[0], ", ".join(x[1])] for x in best_players]

def top_species_scorers(c):
  return top_thing_scorers(c, 'top_species_scores', 'crace')

def top_class_scorers(c):
  return top_thing_scorers(c, 'top_class_scores', 'cls')

def top_combo_scorers(c):
  return top_thing_scorers(c, 'top_combo_scores', 'charabbr')
