import re

V_SPLIT = re.compile(r'(\D+)')
V_DIGITS = re.compile(r'\d+')
V_DESIGNATOR = re.compile(r'-?([a-z]+)(\d*)$')


def extend_list(l, size, defval):
  while len(l) < size:
    l.append(defval)
  return l

def clean(x):
  if x[0] == '-':
    return x[1:]
  return x

def canonical_designator(des):
  m = V_DESIGNATOR.search(des)
  return "%-2s%03d" % (m.group(1),
                       len(m.group(2)) > 0 and int(m.group(2)) or 0)

def split(x):
  has_designator = V_DESIGNATOR.search(x)
  base = x[0:has_designator.start()] if has_designator else x

  designator = has_designator and canonical_designator(has_designator.group())
  pieces = [clean(x) for x in V_SPLIT.split(base)
            if x != '' and x != '.']
  numbers = extend_list([int(x) for x in pieces], 3, 0)
  numbers.append(designator or 'z999')
  return numbers

def version_less_than(a, b):
  """Return True if a < b.

  >>> version_less_than('0.4', '0.4.0')
  False
  >>> version_less_than('0.3', '0.3.1')
  True
  >>> version_less_than('0.9', '0.10')
  True
  >>> version_less_than('0.10', '0.10a')
  False
  >>> version_less_than('0.10a', '0.10')
  True
  >>> version_less_than('0.10a', '0.10-b')
  True
  >>> version_less_than('0.10a', '0.10-a1')
  True
  >>> version_less_than('0.9-rc2', '0.9')
  True
  """
  return split(a) < split(b)

def version_match(a, b):
  """Return True if the two versions match for the major and minor version
  numbers.

  >>> version_match('0.9-a', '0.9.5')
  True
  >>> version_match('0.8', '0.9')
  False
  """
  return split(a)[0:2] == split(b)[0:2]

if __name__ == '__main__':
  import doctest
  doctest.testmod()
