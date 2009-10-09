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

TEMPLATE_DIR = os.path.abspath('templates')
MAKO_LOOKUP = mako.lookup.TemplateLookup(directories = [ TEMPLATE_DIR ])

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
  for p in query.find_all_players(c):
    player_page(c, p)

def player_page(c, player):
  info("Updating player page for %s" % player)
  render(c, 'player',
         dest = ('%s/%s' % (crawl_utils.PLAYER_BASE, player.lower())),
         pars = { 'player' : player, 'quiet': True })

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

def init_dirty(p):
  for p in PAGE_DEFS:
    threshold = len(p) == 1 and DEFAULT_DIRTY_THRESHOLD or p[1]
    DIRTY_PAGES[p[0]] = { 'dirtiness': 0, 'threshold': threshold }

def dirty_player(p, increment = PLAYER_DIRTY_THRESHOLD + 1):
  if first_run:
    return
  if not DIRTY_PLAYERS.has_key(p):
    DIRTY_PLAYERS[p] = { 'dirtiness': 0, 'threshold': PLAYER_DIRTY_THRESHOLD }
  DIRTY_PLAYERS[p]['dirtiness'] += increment
  debug("player_DIRTY: %s (+%d) => %d" % (p, increment, DIRTY_PLAYERS[p]['dirtiness']))

def dirty_page(p, increment = DEFAULT_DIRTY_THRESHOLD + 1):
  if first_run:
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

def incremental_build(c):
  global first_run
  if first_run:
    for p in PAGE_DEFS:
      init_dirty(p)
    first_run = False
    rebuild(c)
    return
  def apply_to_dirty(things, fn, wipe=False):
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
  apply_to_dirty(DIRTY_PAGES, render)
  apply_to_dirty(DIRTY_PLAYERS, player_page, wipe=True)
