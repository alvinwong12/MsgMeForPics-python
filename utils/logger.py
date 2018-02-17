import logging
import datetime

class Logger(object):
  def __init__(self, name=__name__, level=logging.DEBUG):
    self.logger = logging.getLogger(name)
    self.logger.setLevel(level)

  def getLogger(self):
    return self.logger

  def setHandler(self, handler):
    self.handler = handler
    self.logger.addHandler(handler)

  def setFormatter(self, formatter):
    self.formatter = formatter
    self.logger.setFormatter(formatter)