import sources
import yaml

CONFIG_FILE = 'sources.yml'

CONFIG = yaml.load(open(CONFIG_FILE).read())

SOURCES = sources.Sources(CONFIG_FILE)
SCORING_BASE = CONFIG['scoring-base']
USE_MILESTONES = CONFIG['use-milestones']
