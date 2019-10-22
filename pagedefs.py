#!/usr/bin/python

import mako.template
import mako.lookup
import os
import os.path
import scload
import query
import crawl_utils
import locale
import html

from logging import debug, info, warn, error

# Handle input encoding of strings that are actually UTF-8.
# Based on http://stackoverflow.com/a/25235213
def handle_unicode(value):
  if isinstance(value, basestring):
    return unicode(value.decode('utf-8', errors='replace'))
  return unicode(value)

TEMPLATE_DIR = os.path.abspath('templates')
MAKO_LOOKUP = mako.lookup.TemplateLookup(
  directories = [ TEMPLATE_DIR ],
  output_encoding = 'utf-8', encoding_errors = 'replace',
  imports = [ "import pagedefs" ],
  default_filters = [ "pagedefs.handle_unicode" ])

force_locale = html.force_locale

def render(c, page, dest=None, pars=None):
  """Given a db context and a .mako template (without the .mako extension)
  renders the template and writes it back to <page>.html in the tourney
  scoring directory. Setting dest overrides the destination filename."""

  force_locale()

  if not pars or not pars.has_key('quiet'):
    info("Rendering " + page)
  target = "%s/%s.html" % (crawl_utils.SCORE_FILE_DIR, dest or page)
  t = MAKO_LOOKUP.get_template(page + '.mako')
  try:
    f = open(target, 'w')

    pars = pars or { }
    pars['cursor'] = c

    try:
      f.write( t.render( attributes = pars ) )
    finally:
      f.close()
  except Exception, e:
    warn("Error generating page %s: %s" % (page, e))
    raise
    # Don't rethrow.

def render_pages(c):
  for p in PAGE_DEFS:
    render(c, p[0])

def render_player_pages(c):
  for p in query.find_all_players(c):
    player_page(c, p)

def player_page(c, player):
  info("Updating player page for %s" % player)
  render(c, 'player',
         dest = ('%s/%s' % (crawl_utils.PLAYER_BASE, player.lower())),
         pars = { 'player' : player, 'quiet': True })

def player_pages_exist():
  player_dir = crawl_utils.PLAYER_FILE_DIR
  if not os.path.exists(player_dir):
    return False
  try:
    os.rmdir(player_dir) # this is, in a somewhat insane fashion, apparently the
                         # best way to check if a directory containing a large
                         # number of files exists in python 2.7. A non-empty
                         # directory will not be removed.
  except OSError as ex:
    return True
  # We have removed it as a side effect -- recreate. (Does this cause any
  # issues???)
  os.makedirs(crawl_utils.PLAYER_FILE_DIR)
  return False

PAGE_DEFS = [
  [ 'overview' ], #
  [ 'top-N' ], #
  [ 'best-players-total-score' ], #
  [ 'top-combo-scores' ], #
  [ 'combo-scoreboard' ], #
  [ 'all-players' ], #
  [ 'killers' ], #
  [ 'gkills' ], #
  [ 'winners' ], #
  [ 'fastest-wins-turns' ], #
  [ 'fastest-wins-time' ], #
  [ 'streaks' ], #
  [ 'recent' ], #
  [ 'per-day' ], #
]

DIRTY_PAGES = { }
DIRTY_PLAYERS = { }

# Pages update at least once in 30 minutes if dirty.
DEFAULT_DIRTY_THRESHOLD = 30
PLAYER_DIRTY_THRESHOLD = 30

first_run = True

def tick_dirty():
  def tick_thing(things):
    for p in things.keys():
      v = things[p]
      if v['dirtiness']:
        v['dirtiness'] += 1

  tick_thing(DIRTY_PAGES)
  tick_thing(DIRTY_PLAYERS)

def fully_dirty():
  def dirty_thing(things):
    for p in things.keys():
      v = things[p]
      v['dirtiness'] = v['threshold']
  dirty_thing(DIRTY_PAGES)
  dirty_thing(DIRTY_PLAYERS)

def init_dirty():
  for p in PAGE_DEFS:
    threshold = len(p) == 1 and DEFAULT_DIRTY_THRESHOLD or p[1]
    DIRTY_PAGES[p[0]] = { 'dirtiness': 0, 'threshold': threshold }

def dirty_player(p, increment = PLAYER_DIRTY_THRESHOLD + 1):
  if not DIRTY_PLAYERS.has_key(p):
    DIRTY_PLAYERS[p] = { 'dirtiness': 0, 'threshold': PLAYER_DIRTY_THRESHOLD }
  DIRTY_PLAYERS[p]['dirtiness'] += increment
  debug("player_DIRTY: %s (+%d) => %d" % (p, increment, DIRTY_PLAYERS[p]['dirtiness']))

def dirty_page(p, increment = DEFAULT_DIRTY_THRESHOLD + 1):
  if first_run: # TODO: get rid of this
    return
  DIRTY_PAGES[p]['dirtiness'] += increment
  debug("page_DIRTY: %s (+%d) => %d" % (p, increment, DIRTY_PAGES[p]['dirtiness']))

def dirty_pages(*pages):
  for p in pages:
    dirty_page(p)

def mark_all_clean():
  for v in DIRTY_PAGES.values():
    v['dirtiness'] = 0
  DIRTY_PLAYERS.clear()

def rebuild(c):
  render(c, 'index')
  render_pages(c)
  mark_all_clean()

def rebuild_pages(c):
  render_player_pages(c)
  DIRTY_PLAYERS.clear()

def initialize_pages(c):
  global first_run
  init_dirty()
  first_run = False
  render(c, 'index')
  fully_dirty() # set all pages dirty, and any players that have been touched
  if scload.OPT.rebuild_players or not player_pages_exist():
    rebuild_pages(c)

def apply_to_dirty(c, things, fn, wipe=False):
  done = []
  for p in things.keys():
    v = things[p]
    if v['dirtiness'] >= v['threshold']:
      fn(c, p)
      done.append(p)
      v['dirtiness'] = 0
  if wipe:
    for d in done:
      del things[d]

def flush_pages(c):
  fully_dirty()
  # don't render summary pages here because it can be too slow
  apply_to_dirty(c, DIRTY_PLAYERS, player_page, wipe=True)

def incremental_build(c):
  global first_run
  if first_run:
    initialize_pages(c)
  apply_to_dirty(c, DIRTY_PAGES, render)
  apply_to_dirty(c, DIRTY_PLAYERS, player_page, wipe=True)
