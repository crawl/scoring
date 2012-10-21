import xlog.xlog_def
import yaml
import re
from morgue_base import MorgueBase

class Sources (object):
  def __init__(self, definition_file):
    self.definition_file = definition_file
    self._logfiles = None
    self._milestones = None
    self._sources = None
    self._source_map = None
    self._cfg = None

  def cfg(self, key=None):
    if not self._cfg:
      self._cfg = yaml.load(open(self.definition_file).read())
    if key:
      return self._cfg[key]
    return self._cfg

  def sources(self):
    if not self._sources:
      self._sources = self._resolve_sources('sources')
    return self._sources

  def source(self, source_name):
    if not self._source_map:
      self._source_map = dict([[source.name, source]
                                for source in self.sources()])
    return self._source_map[source_name]

  def logfiles(self):
    if not self._logfiles:
      self._logfiles = [log for logs in
                        [src.logfiles() for src in self.sources()]
                        for log in logs]
    return self._logfiles

  def milestones(self):
    if not self._milestones:
      self._milestones = [mile for miles in
                          [src.milestones() for src in self.sources()]
                          for mile in miles]
    return self._milestones

  def _resolve_sources(self, key):
    return [Source(src) for src in self.cfg(key)]

class Source (object):
  def __init__(self, cfg):
    self._cfg = cfg
    self.name = cfg['name']
    self.base = cfg['base']
    self.local = cfg.get('local')
    self._logfiles = None
    self._milestones = None
    self._morgue_bases = None

  def cfg(self, key):
    return self._cfg[key]

  def logfiles(self):
    if not self._logfiles:
      self._logfiles = self._resolve_files('logfiles')
    return self._logfiles

  def milestones(self):
    if not self._milestones:
      self._milestones = self._resolve_files('milestones')
    return self._milestones

  def morgue_bases(self):
    if not self._morgue_bases:
      self._morgue_bases = self._resolve_morgue_bases('morgues')
    return self._morgue_bases

  def _resolve_files(self, key, factory=xlog.xlog_def.XlogDef):
    files = []
    file_type = key[0:-1]
    for path in self.cfg(key):
      files.append(factory(path, source_name=self.name,
                           base_url=self.base, local_base=self.local,
                           xlog_type=file_type))
    return files

  def _resolve_morgue_bases(self, key):
    return [MorgueBase(x) for x in self.cfg(key)]
