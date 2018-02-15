from werkzeug import *
from boto3.dynamodb.conditions import Key, Attr
from response import Response
import random

class Task(object):
	def __init__(self):
		pass

	def Run(self):
		pass

class SelectPhotoTask(Task):
	@staticmethod
	def get_history(database, sms):
		# Get History
		kce = Key('phone').eq(sms['From'])
		fe = Attr('tag').eq(sms['body'])
		history = database.query_user_history(kce, fe)
		history_id = 1 if history['Count'] == 0 else history['Items'][0]['id']
		return history, history_id

	@staticmethod
	def get_photo(database, sms, history):
		kce = Key('tag').eq(sms['body']) & Key('id').eq(history[1] + 1)
		return database.query_photo(kce)

	@staticmethod
	def get_photo_history(database, sms):
		kce = Key('tag').eq(sms['body'])
		photo_history = database.query_photo_history(kce)
		return photo_history

	@staticmethod
	def choose_photo(database, photo_search_client, photo, photo_history, sms, history):
		if photo['Count'] == 0 and photo_history['Count'] == 0:
			# search photo, return first photo, write all to dynamodb (background)
			new_photos = photo_search_client.photosSearch(tags=sms['body'], per_page=500, page=SelectPhotoTask.randnum(8))
			SelectPhotoTask.store_all_photos(database, new_photos, sms['body']) # to be ran in background
			return Response.generateMediaURL(new_photos['photo'][0])
		elif history[1] >= photo_history['Items'][0]['id']:
			# choose random from existing
			kce = Key('tag').eq(sms['body']) & Key('id').eq(SelectPhotoTask.randnum(photo_history['Items'][0]['id']))
			photo = database.query_photo(kce)
			return photo['Items'][0]['url']
		elif photo_history['Items'][0]['id'] - 5 <= history[1] + 1:
			# almost got all the photos, return,  get more photos (background)
			id = photo_history['Items'][0]['id'] + 1
			new_photos = photo_search_client.photosSearch(tags=sms['body'], per_page=500, page=SelectPhotoTask.randnum(8))
			SelectPhotoTask.store_all_photos(database, new_photos, sms['body'], id) # to be ran in background
			return photo['Items'][0]['url']
		else:
			# just return photo
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
		try:
			# Get History
			history = SelectPhotoTask.get_history(dynamodb, sms)# history object contains: entire history object, id
			photo = SelectPhotoTask.get_photo(dynamodb, sms, history)
			photo_history = SelectPhotoTask.get_photo_history(dynamodb, sms)
			# make sure access id doesnt go over photoid
			id = history[1] + 1
			if photo_history['Items'] and photo_history['Items'][0]['id']:
				id = history[1] if history[1] >= photo_history['Items'][0]['id'] else id
			# update
			dynamodb.update_user_history(phone=sms['From'], tag=sms['body'], id=id)
			selected_photo = SelectPhotoTask.choose_photo(dynamodb, flickr_client, photo, photo_history, sms, history)
			return selected_photo
		except Exception as e:
			print str(e)
			return None

	@staticmethod
	def RunRandom(flickr_client, sms):
		return SelectPhotoTask.choose_random_photo(flickr_client, sms)