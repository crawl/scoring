from memoizer import Memoizer
import re
import os
import os.path
import glob
from config import RAWDATA_PATH

import config
from morgue.time import morgue_timestring

from version import version_less_than

R = re.compile
R_MORGUE_TIME = re.compile(r'morgue-\w+-(.*?)\.txt$')
R_SRC_SERVER = re.compile(r'^(\w+)')

def morgue_filename(name, timestr):
  return RAWDATA_PATH + "/" + name + "/morgue-" + name + "-" + timestr + ".txt"

def cao_morgue_url(name, timestr):
  return ("%s/%s/morgue-%s-%s.txt" %
          (config.SOURCES.source('cao').default_morgue_base(),
           name, name, timestr))

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
  if config.RAWDATA_PATH is None:
    return None
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

def morgue_link(g):
  """Given a game dictionary, returns a URL to the game's morgue."""
  source_file = os.path.basename(g['source_file'])
  server = R_SRC_SERVER.search(source_file).group(1)

  try:
    source = config.SOURCES.source(server)
  except KeyError:
    return ''

  name = g['name']
  stime = morgue_timestring( g['end_time'] )
  if version_less_than(g['v'], '0.4'):
    if game_is_cao(g):
      return find_cao_morgue_link(name, stime)
    # Nothing we can do for anyone else with old games.
    return ''
  for morgue_base in source.morgue_bases():
    morgue_url = morgue_base.url(source_file, g)
    if morgue_url:
      return morgue_url

  # Unknown morgue:
  raise Exception("Unknown source for morgues: %s" % src)
