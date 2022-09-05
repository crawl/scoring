import re
import itertools
import morgue.time
import version

class GameMatcher (object):
  """Matches games based on a regex and the logfile name, or an arbitrary
  predicate.

  >>> from datetime import datetime
  >>> bool(GameMatcher('cdo.*-svn').match('cdo-logfile-svn', {}))
  True
  >>> GameMatcher({ 'time_gt': ['end_time', '20110819-1740'],
  ...               'version_match': ['v', '0.9'] }).match('',
  ...             { 'v': '0.9.2', 'end_time': datetime(2011, 8, 19, 17, 42) })
  True
  >>> GameMatcher({ 'time_gt': ['end_time', '20110819-174000'],
  ...               'version_match': ['v', '0.9'] }).match('',
  ...             { 'v': '0.9.2', 'end_time': datetime(2011, 8, 19, 17, 40) })
  False
  >>> GameMatcher({ 'time_gt': ['end_time', '20110819-1740'],
  ...               'version_match': ['v', '0.9'] }).match('',
  ...             { 'v': '0.8', 'end_time': datetime(2011, 8, 19, 17, 45) })
  False
  >>> GameMatcher({ 'time_gt': ['end_time', '20110819-1740'],
  ...               'version_match': ['v', '0.9'] }).match('',
  ...             { 'v': '0.10', 'end_time': datetime(2011, 8, 19, 17, 45) })
  False
  """

  def __init__(self, config):
    self.config = config
    self.regex = None
    self.predicate = None

    if isinstance(config, str):
      self.regex = re.compile(config)
    else:
      self.predicate = GamePredicate(config)

  def __call__(self, *args):
    return self.match(*args)

  def match(self, source, game_dict):
    if self.regex:
      return self.regex.search(source)
    return self.predicate.match(game_dict)

class GamePredicate (object):
  functions = { }

  @classmethod
  def register_function(cls, name, function):
    cls.functions[name] = function
    return function

  @classmethod
  def predicate(cls, name):
    def decorator(predicate_class):
      cls.register_function(name, predicate_class)
      return predicate_class
    return decorator

  @classmethod
  def function_named(cls, function):
    return cls.functions[function]

  def __init__(self, config):
    self.matchers = []
    for function, arguments in config.items():
      self.matchers.append(
        GamePredicate.function_named(function)(*arguments))

  def match(self, game):
    return all(predicate(game) for predicate in self.matchers)

  def __call__(self, *args):
    return self.match(*args)

class FunctionPredicate (object):
  def __init__(self, *args):
    self.args = args

  def __call__(self, *args):
    return self.match(*args)

# TODO: does this actually work??
@GamePredicate.predicate('and')
class AndPredicate (object):
  def __init__(self, *args):
    self.matchers = [GamePredicate(x) for x in args]

  def match(self, game):
    return all(predicate(game) for predicate in self.matchers)

  def __call__(self, *args):
    return self.match(*args)

# TODO: Sequell doesn't implement this
@GamePredicate.predicate('time_lt')
class TimeLessThanPredicate (FunctionPredicate):
  def match(self, game):
    return morgue.time.morgue_timestring(game[self.args[0]]) < self.args[1]

@GamePredicate.predicate('time_gt')
class TimeGreaterThanPredicate (FunctionPredicate):
  def match(self, game):
    return morgue.time.morgue_timestring(game[self.args[0]]) > self.args[1]

@GamePredicate.predicate('version_match')
class VersionMatchPredicate (FunctionPredicate):
  def match(self, game):
    return version.version_match(game[self.args[0]], self.args[1])

if __name__ == '__main__':
  import doctest
  doctest.testmod()
