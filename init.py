from flask import Flask, request
from celery import Celery
from utils.config import Config
from utils.model import DynamoDB
import os
parser = Config().getParser()
parser.read('config/server.ini')

app = Flask(__name__)

app.config['CELERY_BROKER_URL'] = parser.get('celery', 'CELERY_BROKER_URL') if os.environ['PYTHON_ENV'] == "development" else os.environ['REDIS_URL']
app.config['CELERY_RESULT_BACKEND'] = parser.get('celery', 'CELERY_RESULT_BACKEND') if os.environ['PYTHON_ENV'] == "development" else os.environ['REDIS_URL']
app.config['CELERY_TASK_SERIALIZER'] = "json"

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

dynamodb = DynamoDB()

def getFlask():
  return app

def getCelery():
  return celery

def getDynamodb():
  return dynamodb