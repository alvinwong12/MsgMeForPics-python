import os
try:
	os.mkdir( "logs", 0777 );
except:
	pass
	
from flask import request
# app = Flask(__name__)

from init import getFlask, getCelery, getDynamodb
app = getFlask()

celery = getCelery()

from utils.task import SelectPhotoTask
from utils.validate import *
from utils.parse import *
from utils.flickrapi import Flickr
from utils.response import Response
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



global flickr_client
flickr_client = Flickr(api_key= os.environ['FLICKR_API_KEY'],
              api_secret=os.environ['FLICKR_SECRET'],
              oauth_token=os.environ['FLICKR_ACCESS_TOKEN'],
              oauth_token_secret=os.environ['FLICKR_ACCESS_TOKEN_SECRET'])

global dynamodb
dynamodb = getDynamodb()

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
	#x = flickr_client.photosSearch(tags='python', per_page=1, page=1)
	return Response.emoji()


@app.route('/', methods=['GET'])
def index():
	return "MsgMeForPics v2.2"


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

if __name__ == "__main__":
	if os.environ['PYTHON_ENV'] == "development":
		app.run(debug=True)
	else:
		app.run(host = "0.0.0.0", debug=False)
