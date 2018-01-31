from flask import Flask, request
from utils.response import *
from utils.validate import *
from utils.parse import *


app = Flask(__name__)

import subprocess
import os

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


@app.route('/', methods=['GET'])
def index():
	return "MsgMeForPics 1.0.0"

@app.route('/sms', methods=["POST"])
def reply():
	resp = MessagingResponse()
	smsValid = validateSMS(request.form)

	if not smsValid: 
		return str(resp.message("ERROR: Cannot search for a photo")), 200, {'Content-Type':'text/xml'} 

	res = generateTwilioResponse(request.form)
	# Add a message
	msg = resp.message(res['body'])
	if res.get('media', None):
		msg.media(res['media'])

	return str(msg), 200, {'Content-Type':'text/xml'} 


if __name__ == "__main__":
	if os.environ['PYTHON_ENV'] == "development":
		app.run(debug=True);
	else:
		app.run(debug=False);