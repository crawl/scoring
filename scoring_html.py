import query, crawl_utils, time
import scload
import config

from crawl_utils import player_link, linked_text, human_number
from morgue.util import morgue_link
import re
import os.path
import locale

TITLE = "Crawl Scoring (stable and alpha versions)"

try:
  import matplotlib
  matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  MATPLOT = True
except:
  MATPLOT = False

BANNER_IMAGES = \
    { 'pantheon': [ 'thepantheon.png', 'The Pantheon' ],
      'discovered_language': [ 'discoveredlanguage.png',
                               'Discovered Language' ],
      'runic_literacy': [ 'runicliteracy.png', 'Runic Literacy' ],
      'heretic' : [ 'Xomprefersaheretic.png', 'Xom Prefers a Heretic' ],
      'top_player_Nth:1': [ '1player.png', 'Best Player: 1st' ],
      'top_player_Nth:2': [ '2player.png', 'Best Player: 2nd' ],
      'top_player_Nth:3': [ '3player.png', 'Best Player: 3rd' ],
      'top_clan_Nth:1':   [ '1clan.png', 'Best Clan: 1st' ],
      'top_clan_Nth:2':   [ '2clan.png', 'Best Clan: 2nd' ],
      'top_clan_Nth:3':   [ '3clan.png', 'Best Clan: 3rd' ],
      'orb'     : [ 'theorb.png', 'The Orb' ],
      'atheist' : [ 'theatheist.png', 'The Atheist' ],
      'free_will': [ 'freewill.png', 'Free Will' ],
      'ghostbuster': [ 'ghostbuster.png', 'Ghostbuster (TM)' ],
      'moose'   : [ 'mooseandsquirrel.png', 'Moose and Squirrel' ],
      'cartographer': [ 'd1cartographer.png', 'D:1 Cartographer' ],
      'nemelex_choice': [ 'nemechoice.png', "Nemelex' Choice" ],
      'shopaholic': [ 'shopuntilyoudrop.png', 'Shop Until You Drop' ],
      'scythe' : [ 'thescythe.png', 'The Scythe' ] }

STOCK_WIN_COLUMNS = \
    [ ('name', 'Player'),
      ('sc', 'Score', True),
      ('charabbr', 'Character'),
      ('turn', 'Turns'),
      ('dur', 'Duration'),
      ('god', 'God'),
      ('urune', 'Runes'),
      ('end_time', 'Time', True),
      ('v', 'Version'),
      ('server', 'Server')
    ]

EXT_WIN_COLUMNS = \
    [ ('sc', 'Score', True),
      ('charabbr', 'Character'),
      ('god', 'God'),
      ('title', 'Title'),
      ('xl', 'XL'),
      ('turn', 'Turns'),
      ('dur', 'Duration'),
      ('urune', 'Runes'),
      ('end_time', 'Date'),
      ('v', 'Version'),
      ('server', 'Server')
    ]

STOCK_COLUMNS = \
    [ ('name', 'Player'),
      ('sc', 'Score', True),
      ('charabbr', 'Character'),
      ('place', 'Place'),
      ('vmsg', 'End'),
      ('turn', 'Turns'),
      ('dur', 'Duration'),
      ('god', 'God'),
      ('urune', 'Runes'),
      ('end_time', 'Time', True),
      ('v', 'Version'),
      ('server', 'Server')
    ]

EXT_COLUMNS = \
    [ ('sc', 'Score', True),
      ('charabbr', 'Character'),
      ('god', 'God'),
      ('title', 'Title'),
      ('place', 'Place'),
      ('vmsg', 'End'),
      ('xl', 'XL'),
      ('turn', 'Turns'),
      ('dur', 'Duration'),
      ('urune', 'Runes'),
      ('end_time', 'Date'),
      ('v', 'Version'),
      ('server', 'Server')
    ]

WHERE_COLUMNS = \
    [
      ('charabbr', 'Character'),
      ('god', 'God'),
      ('title', 'Title'),
      ('place', 'Place'),
      ('xl', 'XL'),
      ('turn', 'Turns'),
      ('time', 'Time'),
      ('status', 'Status')
    ]

R_STR_DATE = re.compile(r'^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})')

def force_locale():
  # Something resets the locale :/
  locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

def pretty_server(game):
  source = config.SOURCES.log_to_source(game.get('source_file'))
  if not source:
    return ''
  name = source.get_canonical_name()
  url = source.get_cfg("server_url")
  if url:
    return '<a href="%s">%s</a>' % (url, name)
  return name

try:
  long
except:
  long = int # stupid compatibility hack

def fixup_column(col, data, game):
  # show 0 instead of "" for winning game rune counts
  # XX I couldn't figure out how this becomes "" in the first place...
  if col.find('urune') != -1 and not data and game.get('ktyp') == 'winning':
    return 0
  elif col.find('time') != -1:
    return pretty_date(data)
  elif col.find('dur') != -1:
    return pretty_dur(data)
  elif col == 'place' and game.get('ktyp') == 'winning':
    return ''
  elif col == 'server':
    return pretty_server(game)
  elif (isinstance(data, (int,long)) and
        (col == 'sc' or col == 'turn' or col.lower().find('score') != -1)):
    return human_number(data)
  return data

def pretty_dur(dur):
  if not dur:
    return ""
  try:
    secs = dur % 60
  except:
    print("FAIL on %s" % dur)
    raise
  dur /= 60
  mins = dur % 60
  dur /= 60
  hours = dur % 24
  dur /= 24
  days = int(dur)
  stime = "%02d:%02d:%02d" % (hours, mins, secs)
  if days > 0:
    stime = str(days) + ", " + stime
  return stime

try:
  unicode
except:
  unicode = str # stupid compat hack

def pretty_date(date):
  if not date:
    return ''

  if type(date) in [str, unicode]:
    m = R_STR_DATE.search(date)
    if not m:
      return date
    return "%s-%s-%s %s:%s:%s" % (m.group(1), m.group(2), m.group(3),
                                  m.group(4), m.group(5), m.group(6))

  return "%04d-%02d-%02d %02d:%02d:%02d" % (date.year, date.month, date.day,
                                            date.hour, date.minute,
                                            date.second)

def pretty_time(time):
  return "%04d-%02d-%02d %02d:%02d:%02d" % (time.tm_year, time.tm_mon,
                                            time.tm_mday,
                                            time.tm_hour, time.tm_min,
                                            time.tm_sec)

def update_time():
  return '''<div class="updatetime">
            Last updated %s UTC.
            </div>''' % pretty_time(time.gmtime())

def wrap_tuple(x):
  if isinstance(x, tuple):
    return x
  else:
    return (x,)

def is_player_header(header):
  return header in ['Player', 'Captain']

def is_numeric_column(col):
  return (col in ['sc', 'turn', 'v']
          or col.find('%') != -1
          or col.lower().find('score') != -1)

def column_class(cname, data):
  if is_numeric_column(cname):
    return "numeric"
  else:
    return isinstance(data, str) and "celltext" or "numeric"

def streak_legend(found_active):
  return ""

def player_streaks_table(streaks):
  found_active = []
  def rowcls(s):
    if s['active']:
      found_active.append(True)
    return s['active'] and 'active-streak' or ''
  def rowdata(s):
    return [s['ngames'], s['start'], s['end'],
            ", ".join(s['games']), s['breaker']]
  return (table_text(['Wins', 'Start', 'End', 'Games', 'Streak Breaker'],
                     streaks, rowclsfn = rowcls, rowdatafn = rowdata)
          + streak_legend(found_active))

def all_streaks_table(streaks, active=False):
  found_active = []
  def rowcls(s):
    if s['active']:
      found_active.append(True)
    return s['active'] and 'active-streak' or ''
  def rowdata(s):
    return [s['ngames'], s['player'], s['start'], s['end'],
            ", ".join(s['games']), s['breaker']]
  if active:
    heads = ['Wins', 'Player', 'Start', 'Last', 'Games']
  else:
    heads = ['Wins', 'Player', 'Start', 'End', 'Games', 'Streak Breaker']
  return (table_text(heads, streaks, rowclsfn = rowcls, rowdatafn = rowdata)
          + streak_legend(found_active))

def table_text(headers, data, cls='bordered',
               count=True,
               link=None,
               fixup=False,
               width=None,
               rowclsfn=None,
               rowdatafn=None,
               place_column=-1,
               stub_text='No data'):
  force_locale()
  if cls:
    cls = ''' class="%s"''' % cls
  if width:
    width = ' width="%s%%"' % width
  out = '''<table%s%s>\n<tr>''' % (cls or '', width or '')

  headers = [ wrap_tuple(x) for x in headers ]

  if count:
    out += "<th>&nbsp;</th>"
  for head in headers:
    out += "<th>%s</th>" % head[0]
  out += "</tr>\n"
  odd = True

  nrow = 0

  ncols = len(headers) + (count and 1 or 0)
  if not data:
    out += '''<tr><td colspan='%s'>%s</td></tr>''' % (ncols, stub_text)

  nplace = 0
  last_value = None

  for row in data:
    nrow += 1
    rowcls = odd and "odd" or "even"
    if rowclsfn:
      rowcls += " " + rowclsfn(row)
    out += '''<tr class="%s">''' % rowcls
    odd = not odd

    if place_column == -1 or last_value != row[place_column]:
      nplace += 1
    if place_column != -1:
      last_value = row[place_column]

    if count:
      out += '''<td class="numeric">%s</td>''' % nplace

    rdat = rowdatafn and rowdatafn(row) or row

    for c in range(len(headers)):
      val = rdat[c]
      header = headers[c]
      tcls = column_class(header[0], val)
      if fixup:
        val = fixup_column(header[0], val, {})
      out += '''<td class="%s">''' % tcls
      val = str(val)
      if is_player_header(header[0]):
        val = linked_text(val, player_link)
      out += val
      out += '</td>'
    out += "</tr>\n"
  out += '</table>\n'
  return out

def games_table(games, first=None, excluding=None, columns=None,
                including=None, cls='bordered', count=True, win=False):
  columns = columns or (win and STOCK_WIN_COLUMNS or STOCK_COLUMNS)

  # Copy columns.
  columns = list(columns)

  if excluding:
    columns = [c for c in columns if c[0] not in excluding]

  if including:
    for pos, col in including:
      columns.insert(pos, col)

  if first and not isinstance(first, tuple):
    first = (first, 1)

  if first and columns[0][0] != first[0]:
    firstc = [ c for c in columns if c[0] == first[0] ]
    columns = [ c for c in columns if c[0] != first[0] ]
    columns.insert( first[1], firstc[0] )

  if cls:
    cls = ''' class="%s"''' % cls
  out = '''<table%s>\n<tr>''' % (cls or '')
  if count:
    out += "<th></th>"
  for col in columns:
    out += "<th>%s</th>" % col[1]
  out += "</tr>\n"
  odd = True
  ngame = 0

  ncols = len(columns) + (count and 1 or 0)
  if not games:
    out += '''<tr><td colspan='%s'>No games</td></tr>''' % ncols

  for game in games:
    ngame += 1

    ocls = odd and "odd" or "even"
    if game.get('ktyp') == 'winning':
      ocls += " win"

    out += '''<tr class="%s">''' % ocls
    odd = not odd

    if count:
      out += '''<td class="numeric">%s</td>''' % ngame

    for c in columns:
      val = fixup_column(c[0], game.get(c[0]) or '', game)
      tcls = column_class(c[0], val)
      out += '''<td class="%s">''' % tcls

      need_link = len(c) >= 3 and c[2]
      if need_link:
        out += linked_text(game, morgue_link, str(val))
      elif is_player_header(c[1]):
        out += linked_text(val, player_link)
      else:
        out += str(val)
      out += '</td>'
    out += "</tr>\n"
  out += "</table>\n"
  return out

def full_games_table(games, **pars):
  if not pars.get('columns'):
    if 'win' in pars:
      win = pars['win']
    else:
      win = True
    pars['columns'] = win and EXT_WIN_COLUMNS or EXT_COLUMNS
  return games_table(games, **pars)

def ext_games_table(games, win=False, **pars):
  cols = win and EXT_WIN_COLUMNS or EXT_COLUMNS
  pars.setdefault('including', []).append((1, ('name', 'Player')))
  if 'count' not in pars:
    pars['count'] = False
  return games_table(games, columns=cols, **pars)

def combo_highscorers(c, limit=10):
  hs = query.top_combo_scorers(c)
  return table_text( [ 'Highscores', 'Player', 'Characters' ],
                     hs[:limit], count = True, place_column = 0 )

def most_pacific_wins(c, limit=6):
  games = query.most_pacific_wins(c, limit)
  return games_table(games,
                     columns = STOCK_WIN_COLUMNS + [('kills', 'Kills')])

def hyperlink_games(games, field):
  hyperlinks = [ morgue_link(g) for g in games ]
  text = [ '<a href="%s">%s</a>' % (link, g[field])
           for link, g in zip(hyperlinks, games) ]
  return ", ".join(text)

def best_ziggurats(c):
  ziggurats = query.best_ziggurats(c)

  def fixup_ziggurats(zigs):
    for z in zigs:
      z[2] = pretty_date(z[2])
    return zigs

  return table_text( [ 'Player', 'Ziggurat Depth', 'Time' ],
                     fixup_ziggurats(ziggurats) )

def youngest_rune_finds(c):
  runes = query.youngest_rune_finds(c)
  runes = [list(r) for r in runes]
  for r in runes:
    r[3] = pretty_date(r[3])
  return table_text([ 'Player', 'Rune', 'XL', 'Time' ], runes)

def most_deaths_to_uniques(c):
  rows = query.most_deaths_to_uniques(c)
  for r in rows:
    r.insert(1, len(r[1]))
    r[2] = ", ".join(r[2])
  return table_text([ 'Player', '#', 'Uniques', 'Time'], rows)

def streak_table(streaks, active=False):
  # Replace the list of streak games with hyperlinks.
  result = []
  for s in streaks:
    games = s[3]
    game_text = hyperlink_games(games, 'charabbr')
    if active:
      game_text += ", " + s[4]
    row = [s[0], s[1], pretty_date(games[0]['start_time']),
           pretty_date(s[2]), game_text]
    result.append(row)

  return table_text( [ 'Player', 'Streak', 'Start',
                       active and 'Last Win' or 'End', 'Games' ],
                     result )

def best_active_streaks(c):
  return streak_table(query.get_top_active_streaks(c), active=True)

def best_streaks(c):
  streaks = query.get_top_streaks(c)
  return streak_table(streaks)

def whereis(show_name, *players):
  where = [ query.whereis_player(p) for p in players ]
  where = [ w for w in where if w ]
  including = [ ]
  if show_name:
    including.append( (0, ('name', 'Player') ) )

  if not where:
    return ''
  return games_table(where, columns=WHERE_COLUMNS, including=including,
                     count=False)

def _strip_banner_suffix(banner):
  if ':' in banner:
    return banner[ : banner.index(':')]
  return banner

def banner_image(banner):
  banner_subkey = _strip_banner_suffix(banner)
  img = BANNER_IMAGES.get(banner) or BANNER_IMAGES.get(banner_subkey)
  if img and img[0]:
    return (crawl_utils.banner_link(img[0]), img[1])
  return img

def banner_img_for(b, nth):
  return '''<div>
              <img src="%s" alt="%s"
                   title="%s" width="150" height="55"
                   id="banner-%d" class="banner">
              </div>''' % (b[0], b[1], b[1], nth)

def banner_named(name):
  img = banner_image(name)
  return banner_img_for(img, 0)

def banner_images(banners):
  images = [banner_image(x) for x in banners]
  images = [i for i in images if i and i[0]]
  seen_images = set()
  deduped = []
  for i in images:
    if not i[1] in seen_images:
      deduped.append(i)
      seen_images.add(i[1])
  return deduped

def banner_div(all_banners):
  res = ''
  banner_n = 1
  for b in all_banners:
    res += banner_img_for(b, banner_n)
    banner_n += 1
  return res

def _scored_win_text(g, text):
  if g['ktyp'] == 'winning':
    text += '*'
  return text

def player_combo_scores(c, player):
  games = query.get_combo_scores(c, player=player)
  games = [ [ crawl_utils.linked_text(g, morgue_link,
                                      _scored_win_text(g, g['charabbr'])),
              g['sc'] ]
            for g in games ]
  return games

def player_species_scores(c, player):
  games = query.game_hs_species(c, player)

  games = [
    [ crawl_utils.linked_text(g, morgue_link,
                              _scored_win_text(g, g['charabbr'][:2])),
      g['sc'] ]
    for g in games ]
  return games

def player_class_scores(c, player):
  games = query.game_hs_classes(c, player)
  games = [
    [ crawl_utils.linked_text(g, morgue_link,
                              _scored_win_text(g, g['charabbr'][2:])),
      g['sc'] ]
    for g in games ]
  return games

def player_scores_block(c, scores, title):
  asterisk = [ s for s in scores if '*' in s[0] ]
  score_table = (scores
                 and (", ".join([ "%s&nbsp;(%d)" % (s[0], s[1])
                                  for s in scores ]))
                 or "None")
  text = """<h3>%(title)s</h3>
              <div class="inset inline bordered">
                %(score_table)s
              </div>
         """ % {'title': title, 'score_table': score_table}
  if asterisk:
    text += "<p class='fineprint'>* Winning Game</p>"
  return text

def player_wins(wins, **pars):
  return games_table(wins, excluding=['name', 'place'], including=[(2, ('title', 'Title'))], **pars)

def best_players_by_total_score(rows):
  return table_text( [ 'Total Score', 'Player', 'Games Played', 'Games Won',
                       'Win %', 'Best Score', 'Average Score', 'First Game',
                       'Most Recent Game' ],
                     rows, fixup=True )

def all_player_stats(rows):
  return table_text( [ 'Total Score', 'Player', 'Games Played', 'Games Won',
                       'Win %', 'Best XL', 'Best Score', 'Average Score',
                       'First Game', 'Most Recent Game' ],
                     rows, fixup=True )

def top_combo_scores(rows):
  return ext_games_table(rows, count=True, first='charabbr')

def top_thing_scorers(thingname, rows):
  return table_text( ['Scores', 'Player', thingname],
                     rows, place_column=0 )

def curried_scorer(thing):
  return lambda rows: top_thing_scorers(thing, rows)

top_species_scorers = curried_scorer('Species')
top_class_scorers = curried_scorer('Class')
top_combo_scorers = curried_scorer('Character')

def winner_stats(stats):
  return table_text(['Wins', 'Player', 'Games Played', 'Win %',
                     'Max Runes', 'Best Score', 'Total Score', 'Average Score'],
                    stats)

def create_image(filename, stats):
  plt.clf()
  plt.figure(1, figsize=(12,6))
  plt.title('Activity on public servers')

  rstats = list(stats)
  rstats.reverse()

  days = [dict(x) for x in rstats if 'day' in x]
  if (len(days) == 0):
    return

  def rolling_average(l, field, window = 5):
    res = []
    b = []
    prev = None
    for x in l:
      value = x[field]
      b.append(value)
      if len(b) > window:
        b = b[1:]
      v = sum(b) * 1.0 / len(b)
      res.append(v)
    return res

  if len(days) <= 40:
    avg_window = 1
  elif len(days) <= 365 * 4:
    avg_window = 5
  else:
    avg_window = 15

  games = rolling_average(days, 'games', avg_window)
  wins = rolling_average(days, 'wins', avg_window)
  players = rolling_average(days, 'players', avg_window)

  if len(days) <= 40:
    intervals = [x for x in range(0, len(days))]
  elif len(days) <= 365 * 4:
    intervals = [x for x in range(0, len(days))
                    if days[x]['day'].endswith('01')]
  else:
    intervals = [x for x in range(0, len(days))
                    if days[x]['day'].endswith('01-01')]

  point_positions = [x + 0.5 for x in intervals]

  # handle completely empty graphs
  def y_axis_max(l, factor=1.2):
    return len(l) and max(l) * factor or 10.0
  def x_axis_max(l):
    return len(l) and len(l) or 0.0

  plt.subplot(311)
  plt.plot([x + 0.5 for x in range(len(wins))], games, 'b-')
  plt.axis([0, x_axis_max(games), 0, y_axis_max(games)])
  labels = ['' for x in [days[i] for i in intervals]]
  plt.ylabel('Games')
  plt.xticks(point_positions, labels, size = 'xx-small', rotation = 'vertical')
  plt.grid(alpha=0.2, linestyle='-')

  plt.subplot(312)
  plt.plot([x + 0.5 for x in range(len(wins))], players, 'r-')
  plt.axis([0, x_axis_max(players), 0, y_axis_max(players)])
  labels = ['' for x in [days[i] for i in intervals]]
  plt.ylabel('Players')
  plt.xticks(point_positions, labels, size = 'xx-small', rotation = 'vertical')
  plt.grid(alpha=0.2, linestyle='-')

  plt.subplot(313)
  plt.vlines([x + 0.5 for x in range(len(wins))], 0, wins, 'g')
  plt.axis([0, x_axis_max(wins), 0, y_axis_max(wins, 1.5)])
  labels = [x['day'] for x in [days[i] for i in intervals]]
  plt.ylabel('Wins')
  plt.xticks(point_positions, labels, size = 'xx-small', rotation = 'vertical')
  plt.grid(alpha=0.2, linestyle='-')

  plt.savefig(filename)

def date_stats(stats, file_suffix=""):
  if MATPLOT:
    create_image(os.path.join(config.SCORE_FILE_DIR,
                  'date-stats%s.png' % file_suffix),
                  stats)

  def daterowcls(r):
    return 'month' in r and 'date-month' or 'date-day'
  def daterowdata(r):
    return [r.get('day') or r.get('month'),
            r['games'], r['players'], r['wins'], r['winners']]
  return table_text(['Date', 'Games', 'Players', 'Wins', 'Winners'],
                    stats,
                    rowclsfn=daterowcls,
                    rowdatafn=daterowdata,
                    count=False)

def player_stats_cell(cell, thing):
  if cell is None:
    return "<td>&nbsp;</td>"
  elif isinstance(cell, str):
    return "<th>" + cell + "</th>"
  else:
    total = cell.get('race_total') or cell.get('class_total') or cell.get('all_total')
    cls = []
    if total:
      cls.append('stat-total')
    if cell['wins'] > 0:
      cls.append('stat-win')
    text = ''
    def keytext(key):
      return str(cell[key] or '&nbsp;')
    cls.append(thing)
    text += keytext(thing)
    return "<td class='%s'>%s</td>" % (" ".join(cls), text)

def player_stats_matrix(stats, thing):
  res = '<table class="stat-table bordered">'
  for row in stats:
    res += '<tr>' + "".join([player_stats_cell(x, thing) for x in row]) + '</tr>'
  return res + '</table>'

def overall_player_stats(c, player):
  ostats = [ query.overall_player_stats(c, player) ]
  def pstat_row(r):
    return [ r['total_score'], r['games_played'], r['games_won'],
             r['win_perc'], r['best_xl'], r['best_score'], r['avg_score'],
             r['first_game'], r['last_game'] ]
  return table_text(['Total Score', 'Games', 'Wins', 'Win %', 'Best XL',
                     'Best Score', 'Average Score', 'First Game',
                     'Most Recent Game'],
                    ostats, rowdatafn=pstat_row, count=False, fixup=True)
