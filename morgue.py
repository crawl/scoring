from memoizer import Memoizer
import re
import os
import glob
from crawl_utils import RAWDATA_PATH

R = re.compile

MORGUE_BASES = [
 [ R(r'cao-.*'),       'http://crawl.akrasiac.org/rawdata' ],
 [ R(r'cdo.*-0.4$'),   'http://crawl.develz.org/morgues/0.4' ],
 [ R(r'cdo.*-0.5$'),   'http://crawl.develz.org/morgues/0.5' ],
 [ R(r'cdo.*-0.6$'),   'http://crawl.develz.org/morgues/0.6' ],
 [ R(r'cdo.*-0.7'),    'http://crawl.develz.org/morgues/0.7' ],
 [ R(r'cdo.*-svn$'),   'http://crawl.develz.org/morgues/trunk' ],
 [ R(r'cdo.*-zd$'),    'http://crawl.develz.org/morgues/trunk' ],
 [ R(r'cdo.*-spr$'),   'http://crawl.develz.org/morgues/sprint' ],
 [ R(r'rhf.*-0.5$'),   'http://rl.heh.fi/crawl/stuff' ],
 [ R(r'rhf.*-0.6$'),   'http://rl.heh.fi/crawl-0.6/stuff' ],
 [ R(r'rhf.*-0.7$'),   'http://rl.heh.fi/crawl-0.7/stuff' ],
 [ R(r'rhf.*-trunk$'), 'http://rl.heh.fi/trunk/stuff' ],
 [ R(r'rhf.*-spr$'),   'http://rl.heh.fi/sprint/stuff' ],
]

CAO_MORGUE_BASE = 'http://crawl.akrasiac.org/rawdata'
CDO_MORGUE_BASE = 'http://crawl.develz.org/morgues/stable'
R_MORGUE_TIME = re.compile(r'morgue-\w+-(.*?)\.txt$')

def morgue_time_string(raw_time):
  return raw_time[:8] + "-" + raw_time[8:]

def morgue_filename(name, timestr):
  return RAWDATA_PATH + "/" + name + "/morgue-" + name + "-" + timestr + ".txt"

def cao_morgue_url(name, timestr):
  return "%s/%s/morgue-%s-%s.txt" % (CAO_MORGUE_BASE, name, name, timestr)

def cao_morgue_files(name):
  rawmorgues = glob.glob(morgue_filename(name, '*'))
  rawmorgues.sort()
  return rawmorgues

def morgue_binary_search(morgues, guess):
  size = len(morgues)
  if size == 1:
    return guess < morgues[0] and morgues[0]

  s = 0
  e = size
  while e - s > 1:
    pivot = int((s + e) / 2)
    if morgues[pivot] == guess:
      return morgues[pivot]
    elif morgues[pivot] < guess:
      s = pivot
    else:
      e = pivot
  return e < size and morgues[e]

@Memoizer
def find_cao_morgue_link(name, end_time):
  fulltime = end_time
  if os.path.exists(morgue_filename(name, fulltime)):
    return cao_morgue_url(name, fulltime)

  # Drop seconds for really ancient morgues.
  parttime = fulltime[:-2]
  if os.path.exists(morgue_filename(name, parttime)):
    return cao_morgue_url(name, parttime)

  # At this point we have no option but to brute-force the search.
  morgue_list = cao_morgue_files(name)

  # morgues are sorted. The morgue date should be greater than the
  # full timestamp.
  best_morgue = morgue_binary_search(morgue_list,
                                     morgue_filename(name, fulltime))
  if best_morgue:
    m = R_MORGUE_TIME.search(best_morgue)
    if m:
      return cao_morgue_url(name, m.group(1))
  return None

def game_is_cao(g):
  return g['source_file'].find('cao') >= 0

def format_time(time):
  return "%04d%02d%02d-%02d%02d%02d" % (time.year, time.month, time.day,
                                       time.hour, time.minute, time.second)

def morgue_link(g):
  """Given a game dictionary, returns a URL to the game's morgue."""
  src = g['source_file']
  name = g['name']
  stime = format_time( g['end_time'] )
  if g['v'] < '0.4':
    if game_is_cao(g):
      return find_cao_morgue_link(name, stime)
    # Nothing we can do for anyone else with old games.
    return ''
  for regex, url in MORGUE_BASES:
    if regex.search(src):
      return "%s/%s/morgue-%s-%s.txt" % (url, name, name, stime)

  # Unknown morgue:
  raise Exception("Unknown source for morgues: %s" % src)
