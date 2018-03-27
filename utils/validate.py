from werkzeug import *
from pattern.en import wordnet, NOUN, singularize
import google.cloud.vision
import requests
from model import MySQL
import logging
logger = logging.getLogger(__name__)

def validateSMS(incomeSMS):
	if not ('Body' in incomeSMS):
		return False
	elif not incomeSMS['Body']:
		return False
	elif str(incomeSMS['Body']).isspace():
		return False
	else:
		return True


class ValidateImage(object):
  def __init__(self):
    self.vision_client = google.cloud.vision.ImageAnnotatorClient()
    self.VALIDATE_CATEGORY = ['noun.animal']  # add categories to be validated OR 'all'
    self.VALIDATE_CATEGORY = 'all'

  def validate(self, tag, media):
    # check with wordnet
    # if synset continue else return -1
    # check category and decide if verify
    # use google vision api to verify
    # result: 1 -> good (keep image) ; 0 -> bad (discard image) ; -1 -> cannot validate (keep)
    tag = singularize(tag).lower()
    synset = wordnet.synsets(tag, pos=NOUN)
    if not synset:
      return -1
    category = synset[0].lexname
    if self.VALIDATE_CATEGORY == 'all':
      pass
    elif category in self.VALIDATE_CATEGORY:
      pass
      # do not return yet
    else:
      return -1 # not all and cannot be validated

    img = requests.get(media)
    gImage = google.cloud.vision.types.Image(content=img.content)
    response = self.vision_client.label_detection(image=gImage)
    labels = map(lambda d: d.description if d.score > 0.9 else None, response.label_annotations)  
    # check if tag in the detected labels with a good probability (score)
    if tag in labels:
      return 1

    # compare synonyms
    synonyms = synset[0].synonyms
    # check if any synonym in labels
    for synonym in synonyms:
      if singularize(tag).lower() in labels:
        return 1
    return 0

class ValidateUser(object):
  def __init__(self):
    self.db = MySQL()
    self.table = "users"

  def validate(self, user):
    user = self.find(user)
    if user:
      return bool(user[2]) or self.publicPermitted()
    else:
      return False

  def addPermission(self, user):
    record = self.find(user)
    if record:
      query = "UPDATE " + self.table + " SET verified=1 WHERE phone=%s"
      # update
    else:
      # add
      query = "INSERT INTO " + self.table + " (PHONE, VERIFIED) VALUES (%s, 1)"
    var = (str(user),)
    return self.db.writeOperation(query, var)

  def removePermission(self, user):
    record = self.find(user)
    if record:
      query = "UPDATE " + self.table + " SET verified=0 WHERE phone=%s"
      # update
      var = (str(user),)
      return self.db.writeOperation(query, var)
    else:
      return False

  def find(self, user):
    try:
      query = "SELECT * FROM " + self.table + " WHERE phone=%s"
      var = (str(user),)
      result = self.db.readOperation(query, var)
      return result[0]
    except Exception as e:
      # log
      logger.exception(str(e))
      return None

  def removeAllPermission(self):
    try:
      query = "UPDATE %s SET verified=0" %self.table
      return self.db.writeOperation(query)
    except Exception as e:
      logger.exception(str(e))
      return False

  def addAllPermission(self):
    try:
      query = "UPDATE %s SET verified=1" % self.table
      return self.db.writeOperation(query)
    except Exception as e:
      logger.exception(str(e))
      return False

  def publicPermitted(self):
    user = self.find("public")
    if user:
      return bool(user[2])
    else:
      return False

if __name__ == "__main__":
  user = "public"
  v = ValidateUser()
  print v.addPermission(user)