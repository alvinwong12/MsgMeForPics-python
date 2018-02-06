from werkzeug import *

def parseSMS(incomeSMS):
	msg = incomeSMS['Body']
	splited_msg = (str(msg)).strip().split("%")
	param = splited_msg[1].strip() if len(splited_msg) > 1  else "mms"
	sms = {
		'body': splited_msg[0].strip(),
		'param': param
	}
	return sms