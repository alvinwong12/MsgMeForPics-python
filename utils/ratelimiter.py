import redis
import os
from config import Config
import hashlib
import time

# rate / interval
# rate = integer
# interval = integer; unit seconds

## Rate Limiter using token bucket

class RateLimiter(object):
  def __init__(self):
    self.parser = Config().getParser()
    self.parser.read('config/server.ini')
    if os.environ['PYTHON_ENV'] == "development":
      self.redis_url = self.parser.get('redis', 'token_bucket')
    else:
      self.redis_url = os.environ['HEROKU_REDIS_IVORY_URL'] # change URL
    self.redis_server = redis.from_url(self.redis_url)

  def new_user(self, user, rate=None, capacity=None):
    rate = self.parser.get('rate limit', 'rate') if not rate else rate
    capacity = self.parser.get('rate limit', 'capacity') if not capacity else capacity
    rate_limit = { 'tokens': capacity, 'rate': rate, 'timestamp': time.time(), 'capacity': capacity }
    self.redis_server.hmset(self.hash_key(user), rate_limit)

  def check(self, user):
    return bool(self.redis_server.hgetall(self.hash_key(user)))

  def hash_key(self, user):
    key = hashlib.sha224(user).hexdigest()
    return key

  def fill(self, user):
    rate_limit = self.redis_server.hgetall(self.hash_key(user))
    if int(rate_limit['tokens']) < int(rate_limit['capacity']):
      interval = int(self.parser.get('rate limit', 'interval'))
      tokens_to_fill = int(rate_limit['rate']) * (time.time() - float(rate_limit['timestamp'])) / interval
      rate_limit['tokens'] = min( int(rate_limit['tokens']) + int(tokens_to_fill) , int(rate_limit['capacity']) )
      rate_limit['timestamp'] = time.time()
      self.redis_server.hmset(self.hash_key(user), rate_limit)

  def consume(self, user, tokens):
    self.fill(user)
    rate_limit = self.redis_server.hgetall(self.hash_key(user))
    if tokens <= int(rate_limit['tokens']):
      rate_limit['tokens'] = int(rate_limit['tokens']) - tokens
      rate_limit['timestamp'] = time.time()
      self.redis_server.hmset(self.hash_key(user), rate_limit)
      return True
    else:
      return False


if __name__ == "__main__":
  r = RateLimiter()
  user = 'test'
  r.new_user(user)
  print r.check("user")
  # print r.consume(user, 5)
  # print r.consume(user, 1)
  # time.sleep(120)
  # r.check(user)
  # print r.consume(user, 1)
  # r.check(user)