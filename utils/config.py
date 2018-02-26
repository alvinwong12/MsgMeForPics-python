from ConfigParser import SafeConfigParser
import logging

logger = logging.getLogger(__name__)

class Config(object):
  def __init__(self, config_file=None):
    self.parser = SafeConfigParser()
    self.config_file = config_file

  def getParser(self):
    return self.parser