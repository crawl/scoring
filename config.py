import sources
import yaml
import os, os.path
import locale

CONFIG_FILE = 'sources.yml'
locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
LOGFORMAT = "%(asctime)s [%(levelname)s] %(message)s"

# load the config file and set up useful variables in the `config` module
CONFIG = yaml.load(open(CONFIG_FILE).read())

SOURCES = sources.Sources(CONFIG_FILE)
USE_MILESTONES = CONFIG['use-milestones']
LOCALBASE = CONFIG.get('local-base', '.')

SCORING_KEY = CONFIG.get('daemon-name', 'scoresd')
LOCKFILE = os.path.join(LOCALBASE, '%s.lock' % SCORING_KEY)
LOGFILE  = os.path.join(LOCALBASE, '%s.log' % SCORING_KEY)
SCORESD_STOP_REQUEST_FILE = os.path.join(LOCALBASE, '%s.stop' % SCORING_KEY)

SCORE_FILE_DIR = CONFIG.get('scoring-local', 'scoring')
PLAYER_BASE = 'players' # subdirectory under scoring-local
PLAYER_FILE_DIR = os.path.join(SCORE_FILE_DIR, PLAYER_BASE)

# default for running scoring locally -- not useful for server setups
SCORING_BASE_URL = CONFIG.get('scoring-base-url', "file://"
                                            + os.path.abspath(SCORE_FILE_DIR))

IMAGE_BASE_URL = SCORING_BASE_URL + '/images'
PLAYER_BASE_URL =SCORING_BASE_URL + '/players'

OVERVIEW_URL = ('''<a href="%s">Overview</a>''' %
                                            SCORING_BASE_URL + "/overview.html")

RAWDATA_PATH = CONFIG.get('rawdata-base')

MKDIRS = [ SCORE_FILE_DIR, PLAYER_FILE_DIR ]

# TODO: should this be here?
for d in MKDIRS:
  if not os.path.exists(d):
    os.makedirs(d)

# other config setup:
# * games restricted in some way from parts of the leaderboards:
#   see scload.init_game_restrictions. This step requires db access, so can't
#   be done here.
