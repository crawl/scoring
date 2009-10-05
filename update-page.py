#!/usr/bin/python

import mako.template
import mako.lookup
import os
import os.path
import scload
import query
import crawl_utils

from logging import debug, info, warn, error

TEMPLATE_DIR = os.path.abspath('templates')
MAKO_LOOKUP = mako.lookup.TemplateLookup(directories = [ TEMPLATE_DIR ])

def render(c, page, dest=None, pars=None):
  """Given a db context and a .mako template (without the .mako extension)
  renders the template and writes it back to <page>.html in the tourney
  scoring directory. Setting dest overrides the destination filename."""
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

def scoring_overview(c):
  render(c, 'overview')

def player_pages(c):
  for p in PAGE_DEFS:
    render(c, p['name'])
  for p in query.find_all_players(c):
    player_page(c, p)

def player_page(c, player):
  info("Updating player page for %s" % player)
  render(c, 'player',
         dest = ('%s/%s' % (crawl_utils.PLAYER_BASE, player.lower())),
         pars = { 'player' : player, 'quiet': True })

INTERVAL = crawl_utils.UPDATE_INTERVAL
TIMER = [ scload.define_timer( INTERVAL, scoring_overview ),
          scload.define_timer( INTERVAL, player_pages ) ]
LISTENER = [ scload.define_cleanup(scoring_overview),
             scload.define_cleanup(player_pages) ]

PAGE_DEFS = [
  { 'name': 'top-N' },
  { 'name': 'best-players-total-score' },
  { 'name': 'top-combo-scores' },
  { 'name': 'combo-scoreboard' },
  { 'name': 'all-players' },
  { 'name': 'killers' },
  { 'name': 'gkills' },
  { 'name': 'winners' },
  { 'name': 'fastest-wins-turns' },
  { 'name': 'fastest-wins-time' },
  { 'name': 'streaks' },
  { 'name': 'recent' },
  { 'name': 'per-day' },
]

if __name__ == '__main__':
  db = scload.connect_db()
  try:
    for l in LISTENER:
      l.cleanup(db)
  finally:
    db.close()
