import re
from morgue.time import morgue_timestring
from morgue.game_matcher import GameMatcher

R_FIELD = re.compile(r'\$(\w+)\$')
R_GROUP = re.compile(r'\$(\d)')

class MorgueBase (object):
  def __init__(self, _cfg):
    if isinstance(_cfg, list):
      self.pattern = GameMatcher(_cfg[0])
      self.url_base = _cfg[1]
    else:
      self.pattern  = None
      self.url_base = _cfg
    self.has_field_pattern = R_FIELD.search(self.url_base)

  def url(self, source_file, game_dict):
    if not self.pattern:
      return self.resolve_morgue_url(self.url_base, game_dict)

    match = self.pattern.match(source_file, game_dict)
    if match:
      return self.resolve_morgue_url(self.url_base, game_dict, match)

  def resolve_morgue_base(self, url_base, game_dict, match=None):
    def replace_group(submatch):
      if not match:
        raise Exception(("%s includes regexp group match '%s', " +
                           "but the pattern %s had no capture for '%s'") %
                          (url_base, submatch.group(),
                           self.pattern, submatch.group()))
      group_num = int(submatch.group(1))
      return match.group(group_num)

    def replace_field(submatch):
      return game_dict[submatch.group(1)]

    url = R_GROUP.sub(replace_group, R_FIELD.sub(replace_field, url_base))
    if not self.has_field_pattern:
      return url + '/' + game_dict['name']
    return url

  def resolve_morgue_url(self, url_base, game_dict, match=None):
    url = self.resolve_morgue_base(url_base, game_dict, match)
    return url + '/' + self.morgue_filename(game_dict)

  def morgue_filename(self, game_dict):
    return 'morgue-%s-%s.txt' % (game_dict['name'],
                                 morgue_timestring(game_dict['end_time']))
