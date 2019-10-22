import MySQLdb
import scload
import time
import crawl_utils
import sys
import signal
import query
import config

import logging
from logging import debug, info, warn, error

import pagedefs

def signal_handler(signum, frame):
  info("Received signal %i, terminating!", signum)
  raise KeyboardInterrupt # hacky: relies on nothing else catching this

# Can run as a daemon and tail a number of logfiles and milestones and
# update the db.
def interval_work(cursor, interval, master):
  master.tail_all(cursor)

def tail_logfiles(logs, milestones, interval=60):
  db = scload.connect_db()
  scload.init_listeners(db)

  cursor = db.cursor()
  scload.set_active_cursor(cursor, db)
  elapsed_time = 0

  master = scload.create_master_reader()
  scload.bootstrap_known_raceclasses(cursor)
  try:
    while True:
      try:
        interval_work(cursor, interval, master)
        pagedefs.incremental_build(cursor)
        if not interval:
          break
      except IOError, e:
        error("IOError: %s" % e)
      info("Finished batch.");

      time.sleep(interval)
      elapsed_time += interval

      pagedefs.tick_dirty()

      if crawl_utils.scoresd_stop_requested():
        info("Exit due to scoresd stop request.")
        break
  except KeyboardInterrupt: # signal or ctrl-c in non-daemon mode
    pass
  finally:
    info("Flushing player pages and shutting down scoresd db connection")
    pagedefs.flush_pages(cursor) # flush any dirty player pages
    scload.set_active_cursor(None)
    cursor.close()
    db.close()

if __name__ == '__main__':
  daemon = "-n" not in sys.argv
  signal.signal(signal.SIGTERM, signal_handler)
  signal.signal(signal.SIGHUP, signal_handler) # TODO: restart on SIGHUP?
  # n.b. SIGKILL may result in dirty pages not being flushed

  logformat = crawl_utils.LOGFORMAT
  if daemon:
    logging.basicConfig(level=logging.DEBUG,
                        filename = crawl_utils.LOGFILE,
                        format = logformat)
  else:
    logging.basicConfig(level=logging.DEBUG, format = logformat)

  if daemon:
    crawl_utils.daemonize()
  tail_logfiles( config.SOURCES.logfiles(), config.SOURCES.milestones(), 60 )
