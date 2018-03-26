from config import Config
import redis
import os
import hashlib
import cPickle

class Cache(object):
  def __init__(self):
    self.parser = Config().getParser()
    self.parser.read('config/server.ini')
    if os.environ['PYTHON_ENV'] == "development":
      self.redis_url = self.parser.get('redis', 'cache')
    else:
      self.redis_url = os.environ['HEROKU_REDIS_NAVY_URL']
    self.cache_server = redis.from_url(self.redis_url)
    self.TTL = 36 # one hour

  def getCacheServer(self):
    return self.cache_server

  def write(self, key, value):
    hash_key = hashlib.sha224(key).hexdigest()
    self.cache_server.set(hash_key, cPickle.dumps(value))
    self.cache_server.expire(hash_key, self.TTL)

  def read(self, key):
    hash_key = hashlib.sha224(key).hexdigest()
    cache = self.cache_server.get(hash_key)
    if cache:
      # cache hit
      return cPickle.loads(cache)
    else:
      # cache miss
      return None