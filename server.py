import os
try:
	os.mkdir( "logs", 0777 );
except:
	pass
	
from flask import request, render_template
# app = Flask(__name__)

from init import getFlask, getCelery, getDynamodb, getRateLimiter
app = getFlask()

celery = getCelery()

from utils.task import SelectPhotoTask
from utils.validate import *
from utils.parse import *
from utils.flickrapi import Flickr
from utils.response import Response
from utils.validate import ValidateUser
import boto3
# from utils.model import DynamoDB
from decimal import *
import twilio as twilio
from twilio.twiml.messaging_response import MessagingResponse
import logging
from logging.handlers import TimedRotatingFileHandler

from utils.config import Config
parser = Config().getParser()
parser.read('config/server.ini')

import json
import requests


global flickr_client
flickr_client = Flickr(api_key= os.environ['FLICKR_API_KEY'],
              api_secret=os.environ['FLICKR_SECRET'],
              oauth_token=os.environ['FLICKR_ACCESS_TOKEN'],
              oauth_token_secret=os.environ['FLICKR_ACCESS_TOKEN_SECRET'])

global dynamodb
dynamodb = getDynamodb()

global authorize
authorize = ValidateUser()

global rateLimiter
rateLimiter = getRateLimiter()

# Celery
# from celery import Celery
# app.config['CELERY_BROKER_URL'] = parser.get('celery', 'CELERY_BROKER_URL')
# app.config['CELERY_RESULT_BACKEND'] = parser.get('celery', 'CELERY_RESULT_BACKEND')

# celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
# celery.conf.update(app.config)
##

## Logging
logging.basicConfig(level=logging.INFO, datefmt='%m/%d/%Y %I:%M:%S %p', format='%(asctime)s - %(levelname)s - %(message)s')
root = logging.getLogger()
timeFileHandler = TimedRotatingFileHandler(parser.get('log', 'filename'), when=parser.get('log', 'interval_type'), interval=int(parser.get('log', 'interval')))
timeFileHandler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
timeFileHandler.setFormatter(formatter)
sh = logging.StreamHandler()
sh.setFormatter(formatter)
app.logger.addHandler(sh)
app.logger.addHandler(timeFileHandler)
root.addHandler(timeFileHandler)

@app.route('/test', methods=['GET'])
def test():
	return Response.emoji()


@app.route('/', methods=['GET'])
def index():
	return "MsgMeForPics v3.3"


@app.route('/sms', methods=["POST"])
def reply():
	app.logger.info("Inbound sms: %s" %str(request.form))
	# valiate user
	success = authorize.validate(str(request.form.get('From', None)))
	if not success:
		app.logger.error(str(request.form.get('From', None)) + "not authorized")
		return abort(401)
	app.logger.info(str(request.form.get('From', None)) + "authorized")

	# Rate limited
	user = str(request.form.get('From', None))
	if not rateLimiter.check(user):
		rateLimiter.new_user(user)
	request_premitted = rateLimiter.consume(user, 1)

	if not request_premitted:
		app.logger.error("%s is rate limited" %user)
		return "Rate limited. Try again in several minutes", 400

	# actual response
	resp = MessagingResponse()
	smsValid = validateSMS(request.form)
	if not smsValid:
		app.logger.error("Inbound sms validation failed")
		resp.message("Cannot search for a photo %s" %Response.emoji("cry"))
		return str(resp), 200, {'Content-Type':'text/xml'} 

	sms = parseSMS(request.form)

	### Choose Photo
	app.logger.info("Selecting photo from dynamodb")
	selected_photo = SelectPhotoTask.RunNormal(flickr_client, sms)
	# selected_photo = SelectPhotoTask.RunRandom(flickr_client, sms) # for random pics

	### 
	res = Response.generateTwilioResponse(sms, selected_photo)
	# Add a message
	msg = resp.message(res['body'])
	if res.get('media', None):
		msg.media(res['media'])

	app.logger.info("Replying to %s with %s" %(res['from'], str(resp)))
	return str(resp), 200, {'Content-Type':'text/xml'}

@app.route('/addpermission', methods=["POST"])
def add():
	user = str(request.form.get('user', None))
	if user == 'all':
		success = authorize.addAllPermission()
	else:
		success = authorize.addPermission(user)
	return str( json.dumps({'success': success}) ), 200, {'Content-Type': 'application/json'}

@app.route('/removepermission', methods=["POST"])
def remove():
	user = str(request.form.get('user', None))
	if user == 'all':
		success = authorize.removeAllPermission()
	else:
		success = authorize.removePermission(user)
	return str( json.dumps({'success': success}) ), 200, {'Content-Type': 'application/json'}

@app.route('/admin/<action>', methods=["GET"])
def admin(action):
	base_url = request.url_root
	if action.lower() == "add":
		return render_template('admin/show.html', post_url="%saddpermission" %base_url, action=action)
	elif action.lower() == "remove":
		return render_template('admin/show.html', post_url="%sremovepermission" %base_url, action=action)
	else:
		return abort(400)


if __name__ == "__main__":
	if os.environ['PYTHON_ENV'] == "development":
		app.run(debug=True)
	else:
		app.run(host = "0.0.0.0", debug=False)
