from werkzeug import *

def generateTwilioResponse(sms, media=None):
	body = "Here is a picture of %s %s" %(sms['body'], emoji("happy"))
	if not media:
		body = "I found nothing %s" %emoji("cry")
		
	if sms['param'].lower() == "sms" and media:
		body += ". Media URL: %s" %str(media)
		media = None

	response = {
		'body': body,
		'media': media,
	}
	
	return response

def generateMediaURL(media, size="medium"):
	if not media: return None
	SIZES = {
		'small': 'm',
		'square': 's',
		'thumbnail': 't',
		'medium': 'z',
		'large': 'b'
	}
	mediaURL =  "https://farm%s.staticflickr.com/%s/%s_%s_%s.jpg" %(str(media['farm']), str(media['server']), str(media['id']), str(media['secret']), SIZES[size])
	return mediaURL;

def emoji(mood=None):
	EMOJI = {
		'cry': '1F622',
		'happy': '1F604',
		'no-emo': '1F636'
	}
	# Default return no expression face
	emoji_str = "\U000%s" %EMOJI.get(mood.lower(), '1F636')
	return emoji_str.decode('unicode-escape')