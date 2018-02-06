import flickr
import random

class Flickr(object):
	def __init__(self, api_key, api_secret, oauth_token=None, oauth_token_secret=None):
		self.api_key = api_key
		self.api_secret = api_secret
		self.oauth_token = oauth_token
		self.oauth_token_secret = oauth_token_secret
		self.client = flickr.FlickrAPI(api_key, api_secret, oauth_token, oauth_token_secret)

	def photosSearch(self, **kvargs):
		try:
			photos = self.client.get('flickr.photos.search', params=kvargs)
			return photos['photos']
		except Exception as e:
			print e.msg
			print e.code
			return None

	def photoSearchRandom(self, **kvargs):
		temp = kvargs
		temp['per_page'] = 1
		photos = self.photosSearch(**temp)
		if not photos: return None 
		total =int(photos['total'])
		if total == 0: return None 
		page = random.randint(1, total)
		kvargs['page'] = page
		kvargs['per_page'] = 1
		return self.photosSearch(**kvargs)['photo'][0]
