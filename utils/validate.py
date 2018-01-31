from werkzeug import *

def validateSMS(incomeSMS):
	if not ('Body' in incomeSMS):
		return False
	elif str(incomeSMS.get('Body', " ")).isspace():
		return False
	else:
		return True