from flask import Flask, request
from utils.response import *
from utils.validate import *
from utils.parse import *
from utils.flickrapi import Flickr
import subprocess
import os

app = Flask(__name__)

global flickr_client
flickr_client = Flickr(api_key= os.environ['FLICKR_API_KEY'],
              api_secret=os.environ['FLICKR_SECRET'],
              oauth_token=os.environ['FLICKR_ACCESS_TOKEN'],
              oauth_token_secret=os.environ['FLICKR_ACCESS_TOKEN_SECRET'])

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
	x = flickr_client.photosSearch(tags='python', per_page=1, page=1)

	return str(x)


@app.route('/', methods=['GET'])
def index():
	return "MsgMeForPics 1.0.0"


@app.route('/sms', methods=["POST"])
def reply():
	resp = MessagingResponse()
	smsValid = validateSMS(request.form)

	if not smsValid:
		resp.message("ERROR: Cannot search for a photo")
		return str(resp), 200, {'Content-Type':'text/xml'} 

	sms = parseSMS(request.form)
	
	photo = flickr_client.photoSearchRandom(tags=sms['body'], media='photos')
	#media = photos['photos']['photo'][0]
	mediaURL = generateMediaURL(photo)

	res = generateTwilioResponse(sms, mediaURL)
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