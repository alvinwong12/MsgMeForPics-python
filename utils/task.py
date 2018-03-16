from werkzeug import *
from boto3.dynamodb.conditions import Key, Attr
from response import Response
import random
import logging
from config import Config
from init import getCelery, getDynamodb, getCache, getImageValidator
celery = getCelery()
cache = getCache()
image_validator = getImageValidator()

parser = Config().getParser()
parser.read('config/server.ini')
logger = logging.getLogger(__name__)
database = getDynamodb()

import celery.task
from celery.registry import tasks

class StoreAllPhotos(celery.task.Task):
	name = "store_all_photos"

	def __init__(self, *args, **kwargs):
		#super(StoreAllPhotos, self).__init__(*args, **kwargs)
		pass

	def run(self, photos, tag, id=1):
		for photo in photos['photo']:
			url = Response.generateMediaURL(photo)
			try:
				valid = image_validator.validate(tag, url)
				if valid == 1 or valid == -1:
					database.write_item("Pictures", "url", tag=tag, id=id, url=url)
				else:
					raise
			except:
				continue
			id += 1
		logger.info("All images for %s is stored to database" %tag)

tasks.register(StoreAllPhotos)

# Entire file needs to be refactored

# task object: stores all variables and methods which are purpose-specific
# Template - to be further implemented with template functions
class Task(object):
	def __init__(self):
		logger.info("Task created")

	def Run():
		logger.info("Start task run")


# Refactor to remove all static methods
class SelectPhotoTask(Task):
	@staticmethod
	def generateCacheKey(tag, id):
		return "%s%s" %(str(tag), str(id))

	@staticmethod
	def checkCache(key):
		return cache.read(key)

	@staticmethod
	def get_history(sms):
		# Get History
		kce = Key('phone').eq(sms['From'])
		fe = Attr('tag').eq(sms['body'])
		history = database.query_user_history(kce, fe)
		history_id = 0 if history['Count'] <= 0 else history['Items'][0]['id']
		return history, history_id	# Can be done better

	@staticmethod
	def get_photo(sms, history):
 		cache_photo = SelectPhotoTask.checkCache(SelectPhotoTask.generateCacheKey(sms['body'], history[1] + 1))
		if cache_photo:
			logger.critical("CACHE HIT - %s" %cache_photo)
			return cache_photo
		else:
			kce = Key('tag').eq(sms['body']) & Key('id').eq(history[1] + 1)
			photo = database.query_photo(kce)
			if photo['Count'] == 0:
				return None
			else:
				cache.write(SelectPhotoTask.generateCacheKey(sms['body'], history[1]+1), photo['Items'][0]['url'])
				return photo['Items'][0]['url']

	@staticmethod
	def get_photo_history(sms):
		kce = Key('tag').eq(sms['body'])
		photo_history = database.query_photo_history(kce)
		return photo_history

	# method code can be cleaner, needs further refactoring
	# most important method, logging here
	'''
	Cases:
		1. No photo with the specified tag
		2. Trying to fetch a photo with id higher than how many photo are there
		3. A user almost fetched all photo of that tag
		4. None of the above edge cases
	'''
	@staticmethod
	def choose_photo(photo_search_client, photo, photo_history, sms, history):
		if not photo and photo_history['Count'] == 0:
			# search photo, return first photo, write all to dynamodb (background)
			logger.critical("Case 1")
			new_photos = photo_search_client.photosSearch(tags=sms['body'], per_page=int(parser.get('flickr', 'per_page')), page=SelectPhotoTask.randnum(int(parser.get('flickr', 'max_results')) / int(parser.get('flickr', 'per_page')) ))
			#SelectPhotoTask.store_all_photos(database, new_photos, sms['body']) # to be ran in background
			task = StoreAllPhotos.delay(new_photos, sms['body'])
			#####
			logger.info("Photo fetched from database %s" %str(Response.generateMediaURL(new_photos['photo'][0])))
			cache.write(SelectPhotoTask.generateCacheKey(sms['body'], 1), Response.generateMediaURL(new_photos['photo'][0]))
			return Response.generateMediaURL(new_photos['photo'][0])
		elif history[1] >= photo_history['Items'][0]['id']:
			# choose random from existing
			logger.critical("Case 2")
			randid = SelectPhotoTask.randnum(photo_history['Items'][0]['id'])
			# cache first
			cache_photo = SelectPhotoTask.checkCache(SelectPhotoTask.generateCacheKey(sms['body'], randid))
			if cache_photo:
				return cache_photo
			#####
			kce = Key('tag').eq(sms['body']) & Key('id').eq(randid)
			photo = database.query_photo(kce)
			logger.info("Photo fetched from database %s" %str(photo['Items'][0]['url']))
			cache.write(SelectPhotoTask.generateCacheKey(sms['body'], randid), photo['Items'][0]['url'])
			return photo['Items'][0]['url']
		elif photo_history['Items'][0]['id'] - 5 <= history[1] + 1:
			# almost got all the photos, return,  get more photos (background)
			logger.critical("Case 3")
			id = photo_history['Items'][0]['id'] + 1
			new_photos = photo_search_client.photosSearch(tags=sms['body'], per_page=int(parser.get('flickr', 'per_page')), page=SelectPhotoTask.randnum(int(parser.get('flickr', 'max_results')) / int(parser.get('flickr', 'per_page')) ))
			# SelectPhotoTask.store_all_photos(database, new_photos, sms['body'], id) # to be ran in background
			StoreAllPhotos.delay(new_photos, sms['body'], id)
			logger.info("Photo fetched from database %s" %str(photo))
			return photo
		else:
			# just return photo
			logger.critical("Case 4")
			logger.info("Photo fetched from database %s" %str(photo))
			return photo

	@staticmethod
	def choose_random_photo(photo_search_client, sms):
		photo = photo_search_client.photoSearchRandom(tags=sms['body'], media='photos')
		mediaURL = Response.generateMediaURL(photo)
		return mediaURL

	@staticmethod
	def randnum(endpoint=100):
		return random.randint(1, endpoint)

	@staticmethod
	def RunNormal(flickr_client, sms):
		logger.info("Normal task running")
		try:
			# Get History
			history = SelectPhotoTask.get_history(sms)# history object contains: entire history object, id
			photo = SelectPhotoTask.get_photo(sms, history)
			photo_history = SelectPhotoTask.get_photo_history(sms)
			# make sure access id doesnt go over photoid
			id = history[1] + 1 # new id
			if photo_history['Items'] and photo_history['Items'][0]['id']:
				id = history[1] if history[1] >= photo_history['Items'][0]['id'] else id
			# update
			database.update_user_history(phone=sms['From'], tag=sms['body'], id=id)
			selected_photo = SelectPhotoTask.choose_photo(flickr_client, photo, photo_history, sms, history)
			return selected_photo

		except Exception as e:
			logger.exception(str(e))
			return None

	@staticmethod
	def RunRandom(flickr_client, sms):
		try:
			# save to cache
			return SelectPhotoTask.choose_random_photo(flickr_client, sms)
		except Exception as e:
			logger.exception(str(e))
			return None


