import os
import os.path
import logging
import fcntl
import sys
import locale
import re

locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

# Scoring scripts running on greensnark's machines are in debug mode.
SNARK_USER = 'tecumseh'
DEBUG_SCORES = (SNARK_USER in os.getcwd() or
                (os.getenv('PWD') and SNARK_USER in os.getenv('PWD')))

# Update every so often (seconds)
UPDATE_INTERVAL = 21 * 60

LOGFORMAT = "%(asctime)s [%(levelname)s] %(message)s"

LOCK = None

if DEBUG_SCORES:
  BASEDIR = os.getenv('HOME')
else:
  BASEDIR = '/home/snark'

SCORING_KEY = 'scoring'
LOCKFILE = BASEDIR + ('/%s.lock' % SCORING_KEY)
LOGFILE  = (BASEDIR + '/%s.log') % SCORING_KEY
SCORE_FILE_DIR = SCORING_KEY
PLAYER_BASE = 'players'
PLAYER_FILE_DIR = SCORE_FILE_DIR + '/' + PLAYER_BASE

# Use file URLs when testing on greensnark's machines.
CAO_BASE = (DEBUG_SCORES
            and 'file:///var/www/crawl'
            or 'http://crawl.akrasiac.org')
CAO_SCORING_BASE = '%s/%s' % (CAO_BASE, SCORING_KEY)
CAO_IMAGE_BASE = CAO_SCORING_BASE + '/images'
CAO_PLAYER_BASE = '%s/players' % CAO_SCORING_BASE

CAO_OVERVIEW = '''<a href="%s/overview.html">Overview</a>''' % CAO_SCORING_BASE

RAWDATA_PATH = '/var/www/crawl/rawdata'
SCORESD_STOP_REQUEST_FILE = os.path.join(BASEDIR, 'scoresd.stop')

MKDIRS = [ SCORE_FILE_DIR, PLAYER_FILE_DIR ]

for d in MKDIRS:
  if not os.path.exists(d):
    os.makedirs(d)

def write_scoresd_stop_request():
  f = open(SCORESD_STOP_REQUEST_FILE, 'w')
  f.write("\n")
  f.close()

def clear_scoresd_stop_request():
  if os.path.exists(SCORESD_STOP_REQUEST_FILE):
    os.unlink(SCORESD_STOP_REQUEST_FILE)

def scoresd_stop_requested():
  return os.path.exists(SCORESD_STOP_REQUEST_FILE)

def unlock_handle():
  fcntl.flock(LOCK, fcntl.LOCK_UN)

def lock_handle(check_only=True):
  if check_only:
    fcntl.flock(LOCK, fcntl.LOCK_EX | fcntl.LOCK_NB)
  else:
    fcntl.flock(LOCK, fcntl.LOCK_EX)

def lock_or_throw(lockfile = LOCKFILE):
  global LOCK
  LOCK = open(lockfile, 'w')
  lock_handle()

def lock_or_die(lockfile = LOCKFILE):
  global LOCK
  LOCK = open(lockfile, 'w')
  try:
    lock_handle()
  except IOError:
    sys.stderr.write("%s is locked, perhaps there's someone else running?\n" %
                     lockfile)
    sys.exit(1)

def daemonize(lockfile = LOCKFILE):
  global LOCK
  # Lock, then fork.
  LOCK = open(lockfile, 'w')
  try:
    lock_handle()
  except IOError:
    sys.stderr.write(("Unable to lock %s - check if another " +
                      "process is running.\n")
                     % lockfile)
    sys.exit(1)

  print "Starting daemon..."
  pid = os.fork()
  if pid is None:
    raise "Unable to fork."
  if pid == 0:
    # Child
    os.setsid()
    lock_handle(False)
  else:
    sys.exit(0)

def player_link(player):
  return "%s/%s.html" % (CAO_PLAYER_BASE, player.lower())

def banner_link(banner):
  return CAO_IMAGE_BASE + '/' + banner

def linked_text(key, link_fn, text=None):
  link = link_fn(key)
  ltext = str(text or key).replace('_', ' ')
  if link:
    return '<a href="%s">%s</a>' % (link, ltext)
  else:
    return ltext

def human_number(n):
  return locale.format('%d', n, True)
