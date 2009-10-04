import query, crawl_utils, time
import loaddb

from crawl_utils import player_link, linked_text, human_number
import re

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
      ('end_time', 'Time', True)
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
      ('end_time', 'Date')
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
      ('end_time', 'Time', True)
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
      ('end_time', 'Date')
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

def fixup_column(col, data, game):
  if col.find('time') != -1:
    return pretty_date(data)
  elif col.find('dur') != -1:
    return pretty_dur(data)
  elif col == 'place' and game.get('ktyp') == 'winning':
    return ''
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
    print "FAIL on %s" % dur
    raise
  dur /= 60
  mins = dur % 60
  dur /= 60
  hours = dur % 24
  dur /= 24
  days = dur
  stime = "%02d:%02d:%02d" % (hours, mins, secs)
  if days > 0:
    stime = str(days) + ", " + stime
  return stime

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
  return (col in ['sc', 'turn']
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

def all_streaks_table(streaks):
  found_active = []
  def rowcls(s):
    if s['active']:
      found_active.append(True)
    return s['active'] and 'active-streak' or ''
  def rowdata(s):
    return [s['ngames'], s['player'], s['start'], s['end'],
            ", ".join(s['games']), s['breaker']]
  return (table_text(['Wins', 'Player', 'Start', 'End', 'Games',
                      'Streak Breaker'],
                     streaks, rowclsfn = rowcls, rowdatafn = rowdata)
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
        out += r'<a href="%s">' % crawl_utils.morgue_link(game)
      elif is_player_header(c[1]):
        val = linked_text(val, player_link)
      out += str(val)
      if need_link:
        out += '</a>'
      out += '</td>'
    out += "</tr>\n"
  out += "</table>\n"
  return out

def full_games_table(games, **pars):
  if not pars.get('columns'):
    if pars.has_key('win'):
      win = pars['win']
    else:
      win = True
    pars['columns'] = win and EXT_WIN_COLUMNS or EXT_COLUMNS
  return games_table(games, **pars)

def ext_games_table(games, win=False, **pars):
  cols = win and EXT_WIN_COLUMNS or EXT_COLUMNS
  pars.setdefault('including', []).append((1, ('name', 'Player')))
  if not pars.has_key('count'):
    pars['count'] = False
  return games_table(games, columns=cols, **pars)

def combo_highscorers(c, limit=10):
  hs = query.top_combo_scorers(c)
  return table_text( [ 'Highscores', 'Player', 'Characters' ],
                     hs[:limit], count = True, place_column = 1 )

def most_pacific_wins(c, limit=6):
  games = query.most_pacific_wins(c, limit)
  return games_table(games,
                     columns = STOCK_WIN_COLUMNS + [('kills', 'Kills')])

def hyperlink_games(games, field):
  hyperlinks = [ crawl_utils.morgue_link(g) for g in games ]
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
  games = [ [ crawl_utils.linked_text(g, crawl_utils.morgue_link,
                                      _scored_win_text(g, g['charabbr'])),
              g['sc'] ]
            for g in games ]
  return games

def player_species_scores(c, player):
  games = query.game_hs_species(c, player)

  games = [
    [ crawl_utils.linked_text(g, crawl_utils.morgue_link,
                              _scored_win_text(g, g['charabbr'][:2])),
      g['sc'] ]
    for g in games ]
  return games

def player_class_scores(c, player):
  games = query.game_hs_classes(c, player)
  games = [
    [ crawl_utils.linked_text(g, crawl_utils.morgue_link,
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
  return games_table(wins, excluding='name', **pars)

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
                     rows )

def curried_scorer(thing):
  return lambda rows: top_thing_scorers(thing, rows)

top_species_scorers = curried_scorer('Species')
top_class_scorers = curried_scorer('Class')
top_combo_scorers = curried_scorer('Character')

def winner_stats(stats):
  return table_text(['Wins', 'Player', 'Games Played', 'Win %',
                     'Max Runes', 'Best Score', 'Total Score', 'Average Score'],
                    stats)
