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
