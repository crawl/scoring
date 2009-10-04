import MySQLdb
import loaddb
import time
import crawl_utils
import sys

import logging
from logging import debug, info, warn, error

# Can run as a daemon and tail a number of logfiles and milestones and
# update the db.
def interval_work(cursor, interval, master):
  master.tail_all(cursor)

def tail_logfiles(logs, milestones, interval=60):
  db = loaddb.connect_db()
  loaddb.init_listeners(db)

  cursor = db.cursor()
  loaddb.set_active_cursor(cursor)
  elapsed_time = 0

  master = loaddb.create_master_reader()
  try:
    while True:
      try:
        interval_work(cursor, interval, master)
        if not interval:
          break
        loaddb.run_timers(cursor, elapsed_time)
      except IOError, e:
        error("IOError: %s" % e)

      time.sleep(interval)
      elapsed_time += interval

      if crawl_utils.taildb_stop_requested():
        info("Exit due to taildb stop request.")
        break
  finally:
    loaddb.set_active_cursor(None)
    cursor.close()
    loaddb.cleanup_listeners(db)
    db.close()

if __name__ == '__main__':
  daemon = "-n" not in sys.argv

  logformat = crawl_utils.LOGFORMAT
  if daemon:
    logging.basicConfig(level=logging.DEBUG,
                        filename = (crawl_utils.BASEDIR + '/scores.log'),
                        format = logformat)
  else:
    logging.basicConfig(level=logging.DEBUG, format = logformat)

  loaddb.load_extensions()
  if daemon:
    crawl_utils.daemonize()
  tail_logfiles( loaddb.LOGS, loaddb.MILESTONES, 30 )
