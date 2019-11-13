import os
import os.path
import locale
import logging
import fcntl
import sys
import re
import config

LOCK = None

def write_scoresd_stop_request():
  f = open(config.SCORESD_STOP_REQUEST_FILE, 'w')
  f.write("\n")
  f.close()

def clear_scoresd_stop_request():
  if os.path.exists(config.SCORESD_STOP_REQUEST_FILE):
    os.unlink(config.SCORESD_STOP_REQUEST_FILE)

def scoresd_stop_requested():
  return os.path.exists(config.SCORESD_STOP_REQUEST_FILE)

def unlock_handle():
  fcntl.flock(LOCK, fcntl.LOCK_UN)

def lock_handle(check_only=True):
  if check_only:
    fcntl.flock(LOCK, fcntl.LOCK_EX | fcntl.LOCK_NB)
  else:
    fcntl.flock(LOCK, fcntl.LOCK_EX)

def lock_or_throw(lockfile = config.LOCKFILE):
  global LOCK
  LOCK = open(lockfile, 'w')
  lock_handle()

def lock_or_die(lockfile = config.LOCKFILE):
  global LOCK
  LOCK = open(lockfile, 'w')
  try:
    lock_handle()
  except IOError:
    sys.stderr.write("%s is locked, perhaps there's someone else running?\n" %
                     lockfile)
    sys.exit(1)

def daemonize(lockfile = config.LOCKFILE):
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
  return config.PLAYER_BASE_URL + "/%s.html" % (player.lower())

def banner_link(banner):
  return config.IMAGE_BASE_URL + "/" + banner

def linked_text(key, link_fn, text=None):
  link = link_fn(key)
  if text is None:
    text = key
  ltext = str(text).replace('_', ' ')
  if link:
    return '<a href="%s">%s</a>' % (link, ltext)
  else:
    return ltext

def human_number(n):
  return locale.format('%d', n, True)
