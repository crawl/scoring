import os.path
import logging
import fcntl
import sys
import locale

locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

# Update every so often (seconds)
UPDATE_INTERVAL = 21 * 60

LOGFORMAT = "%(asctime)s [%(levelname)s] %(message)s"

LOCK = None
BASEDIR = '/home/snark'
LOCKFILE = BASEDIR + '/scoring.lock'
SCORE_FILE_DIR = 'scoring'
PLAYER_BASE = 'players'
PLAYER_FILE_DIR = SCORE_FILE_DIR + '/' + PLAYER_BASE

CAO_MORGUE_BASE = 'http://crawl.akrasiac.org/rawdata'
CDO_MORGUE_BASE = 'http://crawl.develz.org/morgues/stable'
# Use file URLs when testing on greensnark's machines.
CAO_BASE = (('tecumseh' in os.getcwd())
            and 'file:///var/www/crawl'
            or 'http://crawl.akrasiac.org')
CAO_SCORING_BASE = '%s/scoring' % CAO_BASE
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

class Memoizer (object):
  FLUSH_THRESHOLD = 1000
  """Given a function, caches the results of the function for sets of arguments
  and returns the cached result where possible. Do not use if you have
  very large possible combinations of args, or we'll run out of RAM."""
  def __init__(self, fn, extractor=None):
    self.fn = fn
    self.cache = { }
    self.extractor = extractor or (lambda baz: baz)

  def __call__(self, *args):
    if len(self.cache) > Memoizer.FLUSH_THRESHOLD:
      self.flush()
    key = self.extractor(args)
    if not self.cache.has_key(key):
      value = self.fn(*args)
      self.cache[key] = value
      return value
    return self.cache[key]

  def flush(self):
    self.cache.clear()

  def flush_key(self, *args):
    try:
      del self.cache[args]
    except KeyError:
      pass

  def has_key(self, *args):
    return self.cache.has_key(args)

  def set_key(self, value, *args):
    self.cache[args] = value

  def record(self, args, value):
    self.cache[self.extractor(args)] = value

class DBMemoizer (Memoizer):
  def __init__(self, fn):
    Memoizer.__init__(self, fn, lambda args: args[1:])

def format_time(time):
  return "%04d%02d%02d-%02d%02d%02d" % (time.year, time.month, time.day,
                                       time.hour, time.minute, time.second)

def player_link(player):
  return "%s/%s.html" % (CAO_PLAYER_BASE, player.lower())

def banner_link(banner):
  return CAO_IMAGE_BASE + '/' + banner

def morgue_link(xdict):
  """Returns a hyperlink to the morgue file for a dictionary that contains
  all fields in the games table."""
  src = xdict['source_file']
  name = xdict['name']

  stime = format_time( xdict['end_time'] )
  base = src.find('cao') >= 0 and CAO_MORGUE_BASE or CDO_MORGUE_BASE
  return "%s/%s/morgue-%s-%s.txt" % (base, name, name, stime)

def linked_text(key, link_fn, text=None):
  link = link_fn(key)
  return '<a href="%s">%s</a>' % (link, str(text or key).replace('_', ' '))

def human_number(n):
  return locale.format('%d', n, True)
