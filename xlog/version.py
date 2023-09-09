import re

# XX this matching is really ancient, what is actually still needed?
R_SIMPLE_VERSION = re.compile(r'\d+(?:[.]\d+)+')
R_MINOR_VERSION_ONLY = re.compile(r'(?<=\D)(\d{2})$')
R_GIT_VERSION = re.compile(r'(?i)git|svn|trunk')
# XX annoying to hardcode modes
R_MODES = re.compile(r'-(descent|sprint|seeded)$')

def version(path):
  """Return the Crawl version the logfile at path is, or 'any' if unknown.

  >>> version('allgames.txt')
  'any'
  >>> version('logfile04')
  '0.4'
  >>> version('logfile04-sprint')
  '0.4'
  >>> version('logfilegit')
  'git'
  >>> version('allgames-0.11.txt')
  '0.11'
  >>> version('allgames-0.11-seeded.txt')
  '0.11'
  >>> version('meta/0.10/logfile')
  '0.10'
  >>> version('meta/0.30/logfile-descent')
  '0.30'
  >>> version('meta/git/logfile')
  'git'
  >>> version('scoring/crawl-trunk/logfile')
  'git'
  >>> version('allgames-svn-descent.txt')
  'git'
  >>> version('milestones02.txt')
  '0.2'
  """
  return parse_logfile_path(path)[0]

def parse_logfile_path(path):
  # strip a trailing .txt
  if path.endswith(".txt"):
    path = path[:-4]

  # strip any game modes
  mode_result = R_MODES.search(path)
  if mode_result:
    path = path[:mode_result.span()[0]]
    mode = mode_result.groups()[0]
  else:
    mode = "" # default mode

  def match(r, test=None, transform=None):
    # print(path)
    match_object = r.search(path)
    if match_object:
      groups = match_object.groups()
      value = match_object.group() if len(groups) == 0 else groups[0]
      if not test or test(value):
        return transform(value) if transform else value

  def resolve_minor_version(version):
    return '0.' + version.lstrip('0')

  v = (match(R_SIMPLE_VERSION) or
          match(R_MINOR_VERSION_ONLY, transform = resolve_minor_version) or
          match(R_GIT_VERSION, transform = lambda g: 'git') or
          'any')
  return (v, mode)

def mode(path):
  """Return the game mode for the logfile path, with "" for normal dcss.

  >>> mode('allgames.txt')
  ''
  >>> mode('logfile04')
  ''
  >>> mode('logfile04-sprint')
  'sprint'
  >>> mode('logfilegit')
  ''
  >>> mode('allgames-0.11.txt')
  ''
  >>> mode('allgames-0.11-seeded.txt')
  'seeded'
  >>> mode('meta/0.10/logfile')
  ''
  >>> mode('meta/0.30/logfile-descent')
  'descent'
  >>> mode('meta/git/logfile')
  ''
  >>> mode('scoring/crawl-trunk/logfile')
  ''
  >>> mode('allgames-svn-descent.txt')
  'descent'
  >>> mode('milestones02.txt')
  ''
  """
  return parse_logfile_path(path)[1]

if __name__ == "__main__":
  import doctest
  doctest.testmod()
