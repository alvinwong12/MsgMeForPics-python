from werkzeug import *
from boto3.dynamodb.conditions import Key, Attr
from response import Response
import random
import logging

logger = logging.getLogger(__name__)

# Entire file needs to be refactored

# task object: stores all variables and methods which are purpose-specific
# Template - to be further implemented with template functions
class Task(object):
	def __init__(self):
		logger.info("Task created")

	def Run(self):
		logger.info("Start task run")

class BackgroundTask(Task):
	@staticmethod
	def RunMethod():
		pass


# Refactor to remove all static methods
class SelectPhotoTask(Task):
	@staticmethod
	def get_history(database, sms):
		# Get History
		kce = Key('phone').eq(sms['From'])
		fe = Attr('tag').eq(sms['body'])
		history = database.query_user_history(kce, fe)
		history_id = 0 if history['Count'] == 0 else history['Items'][0]['id']
		return history, history_id	# Can be done better

	@staticmethod
	def get_photo(database, sms, history):
		kce = Key('tag').eq(sms['body']) & Key('id').eq(history[1] + 1)
		return database.query_photo(kce)

	@staticmethod
	def get_photo_history(database, sms):
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
	def choose_photo(database, photo_search_client, photo, photo_history, sms, history):
		if photo['Count'] == 0 and photo_history['Count'] == 0:
			# search photo, return first photo, write all to dynamodb (background)
			logger.critical("Case 1")
			new_photos = photo_search_client.photosSearch(tags=sms['body'], per_page=1, page=SelectPhotoTask.randnum(8))
			SelectPhotoTask.store_all_photos(database, new_photos, sms['body']) # to be ran in background
			logger.info("Photo fetched from database %s" %str(Response.generateMediaURL(new_photos['photo'][0])))
			return Response.generateMediaURL(new_photos['photo'][0])
		elif history[1] >= photo_history['Items'][0]['id']:
			# choose random from existing
			logger.critical("Case 2")
			kce = Key('tag').eq(sms['body']) & Key('id').eq(SelectPhotoTask.randnum(photo_history['Items'][0]['id']))
			photo = database.query_photo(kce)
			logger.info("Photo fetched from database %s" %str(photo['Items'][0]['url']))
			return photo['Items'][0]['url']
		elif photo_history['Items'][0]['id'] - 5 <= history[1] + 1:
			# almost got all the photos, return,  get more photos (background)
			logger.critical("Case 3")
			id = photo_history['Items'][0]['id'] + 1
			new_photos = photo_search_client.photosSearch(tags=sms['body'], per_page=1, page=SelectPhotoTask.randnum(8))
			SelectPhotoTask.store_all_photos(database, new_photos, sms['body'], id) # to be ran in background
			logger.info("Photo fetched from database %s" %str(photo['Items'][0]['url']))
			return photo['Items'][0]['url']
		else:
			# just return photo
			logger.critical("Case 4")
			logger.info("Photo fetched from database %s" %str(photo['Items'][0]['url']))
			return photo['Items'][0]['url']

	@staticmethod
	def store_all_photos(database, photos, tag, id=1):
		for photo in photos['photo']:
			url = Response.generateMediaURL(photo)
			try:
				database.write_item("Pictures", "url", tag=tag, id=id, url=url)
			except:
				continue
			id += 1

	@staticmethod
	def choose_random_photo(photo_search_client, sms):
		photo = photo_search_client.photoSearchRandom(tags=sms['body'], media='photos')
		mediaURL = Response.generateMediaURL(photo)
		return mediaURL

	@staticmethod
	def randnum(endpoint=100):
		return random.randint(1, endpoint)

	@staticmethod
	def RunNormal(dynamodb, flickr_client, sms):
		logger.info("Normal task running")
		try:
			# Get History
			history = SelectPhotoTask.get_history(dynamodb, sms)# history object contains: entire history object, id
			photo = SelectPhotoTask.get_photo(dynamodb, sms, history)
			photo_history = SelectPhotoTask.get_photo_history(dynamodb, sms)
			# make sure access id doesnt go over photoid
			id = history[1] + 1 # new id
			if photo_history['Items'] and photo_history['Items'][0]['id']:
				id = history[1] if history[1] >= photo_history['Items'][0]['id'] else id
			# update
			dynamodb.update_user_history(phone=sms['From'], tag=sms['body'], id=id)
			selected_photo = SelectPhotoTask.choose_photo(dynamodb, flickr_client, photo, photo_history, sms, history)
			return selected_photo
		except Exception as e:
			logger.exception(str(e))
			return None

	@staticmethod
	def RunRandom(flickr_client, sms):
		try:
			return SelectPhotoTask.choose_random_photo(flickr_client, sms)
		except Exception as e:
			logger.exception(str(e))
			return None