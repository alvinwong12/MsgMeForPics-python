from werkzeug import *

def generateTwilioResponse(incomeSMS, media=None, param="mms"):

	body = str(incomeSMS['Body']).strip()

	response = {
		'body': body,
		'media': media,
		'respondTo': incomeSMS.get('From', False)	
	}
	
	return response

