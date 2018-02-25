import os
try:
	os.mkdir( "logs", 0777 );
except:
	pass
	
from flask import Flask, request
from utils.task import *
from utils.validate import *
from utils.parse import *
from utils.flickrapi import Flickr
from utils.response import Response
import boto3
from utils.model import DynamoDB
from decimal import *
import twilio as twilio
from twilio.twiml.messaging_response import MessagingResponse
import logging
from logging.handlers import TimedRotatingFileHandler

app = Flask(__name__)

global flickr_client
flickr_client = Flickr(api_key= os.environ['FLICKR_API_KEY'],
              api_secret=os.environ['FLICKR_SECRET'],
              oauth_token=os.environ['FLICKR_ACCESS_TOKEN'],
              oauth_token_secret=os.environ['FLICKR_ACCESS_TOKEN_SECRET'])

global dynamodb
dynamodb = DynamoDB()

# Celery
from celery import Celery
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)
##

## Logging
logging.basicConfig(level=logging.INFO, datefmt='%m/%d/%Y %I:%M:%S %p', format='%(asctime)s - %(levelname)s - %(message)s')
root = logging.getLogger()
timeFileHandler = TimedRotatingFileHandler("logs/access.log", when="D", interval=1)
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
	#x = flickr_client.photosSearch(tags='python', per_page=1, page=1)
	app.logger.info("hi")
	return Response.emoji()


@app.route('/', methods=['GET'])
def index():
	return "MsgMeForPics 2.0.0"


@app.route('/sms', methods=["POST"])
def reply():
	app.logger.info("Inbound sms: %s" %str(request.form))
	resp = MessagingResponse()
	smsValid = validateSMS(request.form)

	if not smsValid:
		app.logger.error("Inbound sms validation failed")
		resp.message("Cannot search for a photo %s" %Response.emoji("cry"))
		return str(resp), 200, {'Content-Type':'text/xml'} 

	sms = parseSMS(request.form)

	### Choose Photo
	app.logger.info("Selecting photo from dynamodb")
	selected_photo = SelectPhotoTask.RunNormal(dynamodb, flickr_client, sms)
	# selected_photo = SelectPhotoTask.RunRandom(flickr_client, sms) # for random pics

	### 
	res = Response.generateTwilioResponse(sms, selected_photo)
	# Add a message
	msg = resp.message(res['body'])
	if res.get('media', None):
		msg.media(res['media'])

	app.logger.info("Replying to %s with %s" %(res['from'], str(resp)))
	return str(resp), 200, {'Content-Type':'text/xml'}

if __name__ == "__main__":
	if os.environ['PYTHON_ENV'] == "development":
		app.run()
	else:
		app.run(host = "0.0.0.0", debug=False)
