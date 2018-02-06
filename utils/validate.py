from werkzeug import *

def validateSMS(incomeSMS):
	if not ('Body' in incomeSMS):
		return False
	elif not incomeSMS['Body']:
		return False
	elif str(incomeSMS['Body']).isspace():
		return False
	else:
		return True