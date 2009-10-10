# Library to query the database and update scoring information. Raw data entry
# from logfile and milestones is done in scload.py, this is for queries and
# post-processing.

import logging
from logging import debug, info, warn, error

import scload
from scload import Query, query_do, query_first, query_row, query_rows
from scload import query_first_col, query_first_def, game_is_win

import crawl
import crawl_utils
from crawl_utils import DBMemoizer, morgue_link, linked_text, human_number
from crawl_utils import player_link
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
  d = scload.connect_db()
  return d.cursor()

def _filter_invalid_where(d):
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
      d = scload.apply_dbtypes( scload.xlog_dict(line) )
      return _filter_invalid_where(d)
    finally:
      f.close()
  except:
    return None

def row_to_xdict(row):
  return dict( zip(scload.LOG_DB_COLUMNS, row) )

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

  query = Query('SELECT ' + scload.LOG_DB_SCOLUMNS + (' FROM %s' % table))
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
    return int(num) * 100.0 / int(den)

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
      query_row(c, 'SELECT ' + scload.LOG_DB_SCOLUMNS
                + ''' FROM player_best_games WHERE name = %s
                     ORDER BY sc DESC LIMIT 1''',
                player)))

def player_first_game(c, player):
  return (row_to_xdict(
      query_row(c, 'SELECT ' + scload.LOG_DB_SCOLUMNS
                + ''' FROM player_first_games WHERE name = %s''',
                player)))

def player_last_game(c, player):
  return (row_to_xdict(
      query_row(c, 'SELECT ' + scload.LOG_DB_SCOLUMNS
                + ''' FROM player_last_games WHERE name = %s''',
                player)))

def calc_avg_int(num, den):
  if den == 0:
    return 0
  else:
    return int(num / den)

def game_select_from(table):
  return "SELECT " + scload.LOG_DB_SCOLUMNS + " FROM " + table + " "

def player_best_first_last(c, player):
  fields = scload.LOG_DB_SCOLUMNS
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
                            FROM players WHERE total_score > 500
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
                    " ORDER BY charabbr")
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

def find_all_players(c):
  return query_first_col(c, '''SELECT name FROM players''')

def player_wins(c, player):
  return find_games(c, 'wins', name = player, sort_min = 'end_time')

def find_streak_breaker(c, sid):
  return row_to_xdict(
    query_row(c, game_select_from('streak_breakers') + " WHERE streak_id = %s",
              sid))

def extract_streaks(c, query, streak_filter=None, max_streaks=None):
  sgames = query.rows(c)
  # Streak table: ngames, active, all games in streak.
  streak_id_map = { }
  def register_game(g):
    if streak_filter and not streak_filter(g):
      return
    sid = g[0]
    if not streak_id_map.has_key(sid):
      breaker = ''
      # If the streak is not active, grab the breaker:
      if not g[5]:
        breaker = find_streak_breaker(c, sid)
        if breaker:
          breaker = linked_text(breaker, morgue_link, breaker['charabbr'])
      streak_id_map[sid] = {'ngames': g[2],
                            'player': g[1],
                            'start': g[3],
                            'end': g[4],
                            'active': g[5],
                            'games': [],
                            'breaker': breaker}
    smap = streak_id_map[sid]
    game = row_to_xdict(g[6:])
    smap['games'].append(linked_text(game, morgue_link, game['charabbr']))

  for g in sgames:
    register_game(g)

  streaks = streak_id_map.values()

  def streak_comparator(a, b):
    bn = b['ngames']
    an = a['ngames']
    if bn == an:
      be = b['end']
      ae = a['end']
      return ((ae < be and -1) or
              (ae > be and 1) or
              0)
    else:
      return int(bn - an)

  streaks.sort(streak_comparator)
  return max_streaks and streaks[:max_streaks] or streaks

def all_streaks(c, max_per_player=10, max_streaks=None, active_streaks=False):
  logf = logfields_prefixed('g.')

  extra = ''
  if active_streaks:
    extra = 's.active = 1 AND '
  q = Query("SELECT s.id, s.player, s.ngames, s.start_game_time, " +
            "s.end_game_time, s.active, " + logf +
            ''' FROM streaks s, streak_games g
               WHERE %s g.name = s.player
                 AND g.end_time >= s.start_game_time
                 AND g.end_time <= s.end_game_time
            ORDER BY s.ngames DESC, s.id''' % extra)

  pscounts = { }
  def player_streak_filter(g):
    player = g[1]
    if not pscounts.has_key(player):
      pscounts[player] = set()
    s = pscounts[player]
    s.add(g[0])
    return len(s) <= max_per_player

  return extract_streaks(c, q, streak_filter = player_streak_filter,
                         max_streaks = max_streaks)

def player_streaks(c, player, max_streaks = 100):
  """Returns a list of streaks for a player, ordered by longest streak
first."""
  logf = logfields_prefixed('g.')
  q = Query("SELECT s.id, s.player, s.ngames, s.start_game_time, " +
            "s.end_game_time, s.active, " + logf +
            ''' FROM streaks s, streak_games g
               WHERE s.player = %s AND g.name = s.player
                 AND g.end_time >= s.start_game_time
                 AND g.end_time <= s.end_game_time
            ORDER BY s.ngames DESC, s.id''',
            player)
  return extract_streaks(c, q, max_streaks = max_streaks)

def player_recent_games(c, player, limit=15):
  return find_games(c, 'player_recent_games',
                    sort_max = 'end_time',
                    name = player,
                    limit = limit)

def player_top_thing_scores(c, player, table, label):
  return [(linked_text(g, morgue_link, g[label])
           + (game_is_win(g) and '*' or ''),
           g['sc'])
          for g in
          find_games(c, table, name=player, sort_max='sc')]

def curry_player_top_thing(table, label):
  return lambda c, player: player_top_thing_scores(c, player, table, label)

player_combo_highscores = curry_player_top_thing('top_combo_scores', 'charabbr')
player_species_highscores = curry_player_top_thing('top_species_scores',
                                                   'raceabbr')
player_class_highscores = curry_player_top_thing('top_class_scores',
                                                 'clsabbr')

def logfields_prefixed(prefix):
  return ",".join([prefix + x for x in scload.LOG_DB_COLUMNS])

def top_killers(c):
  deaths = query_first(c, '''SELECT SUM(kills) FROM top_killers''')
  logf = logfields_prefixed('k.')
  rows = query_rows(c,
                    "SELECT t.ckiller, t.kills, " +
                    logf +
                    ''' FROM top_killers t, killer_recent_kills k
                       WHERE t.ckiller = k.ckiller
                         AND t.ckiller NOT IN ('leaving', 'quitting', 'winning')
                       ORDER BY t.kills DESC, t.ckiller''')
  def fix_killer_row(r):
    perc = calc_perc_pretty(r[1], deaths) + '%'
    g = row_to_xdict(r[2:])
    return [r[0], perc, r[1], linked_text(g, morgue_link, g['name'])]
  return [fix_killer_row(x) for x in rows]

def kill_list(rows):
  ghost_map = { }

  def record_kill(ghost, victim):
    if not ghost_map.has_key(ghost):
      ghost_map[ghost] = { }
    vmap = ghost_map[ghost]
    if not vmap.has_key(victim):
      vmap[victim] = 1
    else:
      vmap[victim] += 1

  for r in rows:
    record_kill(r[0], r[1])

  ghost_items = [list(x) for x in ghost_map.items()]

  def ntimes(count, who):
    if count == 1:
      return who
    return "%s (%d)" % (who, count)

  for g in ghost_items:
    g[1] = g[1].items()
    g[1].sort(lambda a, b: b[1] - a[1])
    g.insert(1, sum([x[1] for x in g[1]]))
    g[2] = ", ".join([ntimes(x[1], x[0]) for x in g[2]])

  ghost_items.sort(lambda a, b: b[1] - a[1])
  return ghost_items

def gkills(c):
  return kill_list(query_rows(c,
                              '''SELECT ghost, victim FROM ghost_victims'''))

def gvictims(c):
  return kill_list(query_rows(c,
                              '''SELECT victim, ghost FROM ghost_victims'''))

def winner_stats(c):
  rows = query_rows(c,
                    '''SELECT p.games_won, p.name, p.games_played,
                              p.max_runes, p.best_score, p.total_score, '''
                    + logfields_prefixed('g.') +
                    '''  FROM players p, player_best_games g
                        WHERE p.name = g.name AND p.best_score = g.sc
                          AND p.games_won > 0
                        ORDER BY p.games_won DESC, p.games_played,
                                 p.best_score DESC''')
  results = []
  for r in rows:
    results.append(list(r[0:3]) +
                   [calc_perc_pretty(r[0], r[2]) + '%', r[3],
                    linked_text(row_to_xdict(r[6:]), morgue_link,
                                human_number(r[4])),
                    human_number(r[5]),
                    human_number(calc_avg_int(r[5], r[2]))])
  return results

def get_fastest_time_player_games(c, limit=5):
  return find_games(c, 'wins', sort_min='dur', limit=limit)

def get_fastest_turn_player_games(c, limit=5):
  return find_games(c, 'wins', sort_min='turn', limit=limit)

def recent_wins(c, limit=5):
  return find_games(c, 'wins', sort_max='end_time', limit=limit)

def recent_allrune_wins(c, limit=5):
  return find_games(c, 'wins', urune=15, sort_max='end_time', limit=limit)

def most_pacific_wins(c, limit=5):
  return xdict_rows(
    query_rows(c,
               game_select_from('wins') +
               # This filters all games where the statistic is unavailable.
               """ WHERE kills > 0
                ORDER BY kills, id LIMIT %s""",
               limit))

def youngest_rune_finds(c, limit=6):
  return query_rows(c, '''SELECT player, rune, xl, rune_time
                            FROM low_xl_rune_finds
                          ORDER BY xl, rune_time LIMIT %s''', limit)

def best_ziggurats(c, limit=6):
  return [list(r) for r in
          query_rows(c, '''SELECT player, place, zig_time
                            FROM ziggurats
                          ORDER BY deepest DESC, zig_time DESC''')]

@DBMemoizer
def count_players_per_day(c, day):
  return query_first(c,
                     '''SELECT COUNT(*) FROM date_players
                                       WHERE which_day = %s''',
                     day)

@DBMemoizer
def winners_for_day(c, day):
  return query_rows(c,
                    '''SELECT player, wins FROM date_players
                        WHERE which_day = %s AND wins > 0
                        ORDER BY wins DESC, player''',
                    day)

def per_day_stats(c, day, fullday, games_ended, games_won):
  distinct_players = count_players_per_day(c, day)
  winners = winners_for_day(c, day)
  return {'day': fullday.strftime('%Y-%m-%d'),
          'games': games_ended,
          'players': distinct_players,
          'wins': games_won,
          'winners': winners}

def string_date(d):
  assert(isinstance(d, datetime))
  return d.strftime('%Y%m%d')

def counted_thing(thing, n):
  if n == 1:
    return thing
  else:
    return "%s (%d)" % (thing, n)

def fixup_winners(winners):
  def plink(p):
    return linked_text(p, player_link)
  return ", ".join([counted_thing(plink(x[0]), x[1]) for x in winners])

def fixup_month(c, month):
  mwin = month['winners'].items()
  month['players'] = query_first(c, '''SELECT COUNT(DISTINCT player)
                                        FROM date_players
                                       WHERE which_month = %s''',
                                 month['month'].replace('-', ''))
  def sort_winners(a, b):
    if a[1] != b[1]:
      return int(b[1] - a[1])
    else:
      return (a[1] < b[1] and -1) or (a[1] > b[1] and 1) or 0
  mwin.sort(sort_winners)
  month['winners'] = fixup_winners(mwin)
  return month

def date_stats(c):
  dates = query_rows(c,
                     '''SELECT which_day, games_ended, games_won
                         FROM per_day_stats ORDER BY which_day DESC''')
  result = []

  month = [None]

  def new_month_stat(this_month):
    return { 'month': this_month,
             'games': 0,
             'players': 0,
             'wins': 0,
             'winners': { } }

  def flush_month(month):
    if not month:
      return
    result.append(fixup_month(c, month))

  def inc_month_stats(date, eday, stats):
    this_month = date.strftime('%Y-%m')
    if not month[0] or month[0]['month'] != this_month:
      flush_month(month[0])
      month[0] = new_month_stat(this_month)
    m = month[0]
    m['games'] += stats['games']
    m['wins'] += stats['wins']
    mwinners = m['winners']
    for wstat in stats['winners']:
      if not mwinners.has_key(wstat[0]):
        mwinners[wstat[0]] = 0
      mwinners[wstat[0]] += wstat[1]

  def record_date(d):
    date = d[0]
    edate = string_date(d[0])
    stats = per_day_stats(c, edate, d[0], d[1], d[2])
    inc_month_stats(date, edate, stats)
    stats['winners'] = fixup_winners(stats['winners'])
    result.append(stats)

  for d in dates:
    record_date(d)

  flush_month(month[0])
  return result

@DBMemoizer
def all_classes(c):
  scload.bootstrap_known_raceclasses(c)
  clx = query_first_col(c, '''SELECT cls FROM known_classes''')
  clx.sort()
  return clx

@DBMemoizer
def all_races(c):
  scload.bootstrap_known_raceclasses(c)
  races = query_first_col(c, '''SELECT race FROM known_races''')
  races.sort()
  return races

def player_get_stats(c, player):
  stats = { }
  rows = query_rows(c, '''SELECT charabbr, games_played, best_xl, wins
                            FROM player_char_stats
                           WHERE name = %s''', player)
  for r in rows:
    stats[r[0]] = { 'games': r[1],
                    'xl': r[2],
                    'wins': r[3] }
  return stats

def player_stats_matrix(c, player):
  races = all_races(c)
  classes = all_classes(c)
  rows = []
  stats = player_get_stats(c, player)

  rows.append(['&nbsp;'] + classes + ['&nbsp;&nbsp;', '&nbsp;'])

  cstats = [ {'class_total': True,
              'games': 0,
              'wins': 0,
              'xl': 0} for c in classes ]

  for r in races:
    row = [ r ]

    rgames = 0
    rwins = 0
    rxl = 0
    for i in range(len(classes)):
      c = classes[i]
      char = r + c
      s = stats.get(char)
      row.append(s)
      if s:
        rgames += s['games']
        cstats[i]['games'] += s['games']
        rwins += s['wins']
        cstats[i]['wins'] += s['wins']
        if s['xl'] > rxl:
          rxl = s['xl']
        if s['xl'] > cstats[i]['xl']:
          cstats[i]['xl'] = s['xl']
    row.append({ 'race_total': True,
                 'games': rgames,
                 'wins': rwins,
                 'xl': rxl })
    row.append(r)
    rows.append(row)

  rows.append(['&nbsp;'] + cstats + ['&nbsp;', '&nbsp;'])
  rows.append(['&nbsp;'] + classes + ['&nbsp;', '&nbsp;'])

  return rows
