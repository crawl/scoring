import os.path
import xlog.version
import errno

XLOG_LOCAL_STAGE = 'data'

def xlog_resolve_source_path(path, local_base, source_base_url):
  """Given a relative path and a source definition, looks up the full path to
  the source."""
  if local_base:
    localpath = os.path.join(local_base, path)
    if os.path.exists(localpath):
      return localpath, True

  return (source_base_url + '/' + path, False)

class XlogDef (object):
  """Metadata on a logfile/milestones file: its associated server,
  path on the local filesystem, remote path, and whether the source is
  filesystem-local or remote."""

  def __init__(self, remote_path, source_name, base_url, local_base, dormant, xlog_type):
    self.raw_path = remote_path
    self.source = source_name
    self.xlog_type = xlog_type
    self.local_base = local_base
    self.source_path, self.local = self._resolve_path(remote_path, local_base,
                                                      base_url)
    self.dormant = dormant
    self.version = xlog.version.version(self.raw_path)
    self.mode = xlog.version.mode(self.raw_path)
    self.local_path = self._local_path(self.source,
                                       self.xlog_type,
                                       self.version)

  def _local_path(self, source, xlog_type, version):
    return os.path.join(XLOG_LOCAL_STAGE,
                        "%s-%s-%s" % (source, xlog_type, version))

  def prepare(self):
    if self.dormant:
      return
    try:
      os.makedirs(os.path.dirname(self.local_path))
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise
    if self.local and not os.path.exists(self.local_path):
      os.symlink(self.source_path, self.local_path)

  def fetch(self):
    if self.local or self.dormant:
      return
    # Use a 20 minute total limit to network activity with a 30 second
    # connection timeout. Use `-C -` to resume downloads based on local+remote
    # file sizes.
    command = "curl --max-time 1200 --connect-timeout 30 -C - -s -o %s %s" % (self.local_path, self.source_path)
    res = os.system(command)
    if res != 0:
      raise IOError("Failed to fetch %s with %s" % (self.source_path, command))

  def _resolve_path(self, path, local_base, base_url):
    return xlog_resolve_source_path(path, local_base, base_url)
