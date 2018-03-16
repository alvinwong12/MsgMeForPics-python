from werkzeug import *
from pattern.en import wordnet, NOUN, singularize
import google.cloud.vision
import requests

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
