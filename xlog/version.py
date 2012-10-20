import re

R_SIMPLE_VERSION = re.compile(r'\d+(?:[.]\d+)+')
R_MINOR_VERSION_ONLY = re.compile(r'(?<=\D)(\d{2})(?:\.txt)?$')
R_GIT_VERSION = re.compile(r'(?i)git|svn|trunk')

def version(path):
  """Return the Crawl version the logfile at path is, or 'any' if unknown.

  >>> version('allgames.txt')
  'any'
  >>> version('logfile04')
  '0.4'
  >>> version('logfilegit')
  'git'
  >>> version('allgames-0.11.txt')
  '0.11'
  >>> version('meta/0.10/logfile')
  '0.10'
  >>> version('meta/git/logfile')
  'git'
  >>> version('scoring/crawl-trunk/logfile')
  'git'
  >>> version('allgames-svn.txt')
  'git'
  >>> version('milestones02.txt')
  '0.2'
  """
  def match(r, test=None, transform=None):
    match_object = r.search(path)
    if match_object:
      groups = match_object.groups()
      value = match_object.group() if len(groups) == 0 else groups[0]
      if not test or test(value):
        return transform(value) if transform else value

  def resolve_minor_version(version):
    return '0.' + version.lstrip('0')

  return (match(R_SIMPLE_VERSION) or
          match(R_MINOR_VERSION_ONLY, transform = resolve_minor_version) or
          match(R_GIT_VERSION, transform = lambda g: 'git') or
          'any')

if __name__ == "__main__":
  import doctest
  doctest.testmod()
