from flask import Flask, request
from utils.task import *
from utils.validate import *
from utils.parse import *
from utils.flickrapi import Flickr
from utils.response import Response
import subprocess
import os
import boto3
from utils.model import DynamoDB
from decimal import *

app = Flask(__name__)

global flickr_client
flickr_client = Flickr(api_key= os.environ['FLICKR_API_KEY'],
              api_secret=os.environ['FLICKR_SECRET'],
              oauth_token=os.environ['FLICKR_ACCESS_TOKEN'],
              oauth_token_secret=os.environ['FLICKR_ACCESS_TOKEN_SECRET'])

global dynamodb
dynamodb = DynamoDB()

def importTwilio():
	import twilio as twilio
	from twilio.twiml.messaging_response import MessagingResponse

	global twilio
	global MessagingResponse

try:
	importTwilio()
	print "twilio imported"
except:
	exit_code = subprocess.call(['pip' , 'install', 'twilio'])
	importTwilio()
	print exit_code


@app.route('/test', methods=['GET'])
def test():
	#x = flickr_client.photosSearch(tags='python', per_page=1, page=1)
	return Response.emoji()


@app.route('/', methods=['GET'])
def index():
	return "MsgMeForPics 2.0.0"


@app.route('/sms', methods=["POST"])
def reply():
	resp = MessagingResponse()
	smsValid = validateSMS(request.form)

	if not smsValid:
		resp.message("Cannot search for a photo %s" %Response.emoji("cry"))
		return str(resp), 200, {'Content-Type':'text/xml'} 

	sms = parseSMS(request.form)

	### Choose Photo
	selected_photo = SelectPhotoTask.RunNormal(dynamodb, flickr_client, sms)
	# selected_photo = SelectPhotoTask.RunRandom(flickr_client, sms) # for random pics

	### 
	res = Response.generateTwilioResponse(sms, selected_photo)
	# Add a message
	msg = resp.message(res['body'])
	if res.get('media', None):
		msg.media(res['media'])

	return str(resp), 200, {'Content-Type':'text/xml'} 


if __name__ == "__main__":
	if os.environ['PYTHON_ENV'] == "development":
		app.run(debug=True);
	else:
		app.run(host = "0.0.0.0", debug=False);