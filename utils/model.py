import boto3
from boto3.dynamodb.conditions import Key, Attr
import MySQLdb
import urlparse
import os
import logging
logger = logging.getLogger(__name__)

class DynamoDB(object):
  def __init__(self, region='us-east-1', endpoint=None):
    self.region = region
    self.endpoint = endpoint
    self.dynamodb = boto3.resource('dynamodb', region_name=region, endpoint_url=endpoint)

  def create_table(self, table_name, partition_key, partition_key_type, sort_key, sort_key_type):
    key_schema = [{'AttributeName': partition_key, 'KeyType': 'HASH'}, {'AttributeName': sort_key, 'KeyType': 'RANGE'}]
    attribute_definitions = [{'AttributeName': partition_key, 'AttributeType': partition_key_type}, {'AttributeName': sort_key, 'AttributeType': sort_key_type}, {'AttributeName': 'id', 'AttributeType': 'N'}]
    local_secondary_indexes = [{
      'IndexName': 'History_ID', 
      'KeySchema':[{
        'AttributeName': partition_key, 
        'KeyType': 'HASH'
      }, {
        'AttributeName': 'id',
        'KeyType': 'RANGE'
      }],
      'Projection': {
        'ProjectionType': 'KEYS_ONLY'
      }
    }]
    table = self.dynamodb.create_table(
      TableName = table_name,
      KeySchema = key_schema,
      AttributeDefinitions = attribute_definitions,
      ProvisionedThroughput={
          'ReadCapacityUnits': 5,
          'WriteCapacityUnits': 5
      },
      LocalSecondaryIndexes=local_secondary_indexes
    )

  def write_item(self, table_name, prevent_ow_attr=None, **kvargs):
    table = self.dynamodb.Table(table_name)
    item = {}
    for key, value in kvargs.iteritems():
      item[key] = value

    params = {
      'Item': item,
      'ConditionExpression': Attr(prevent_ow_attr).not_exists()
    }
    if not prevent_ow_attr:
      del params['ConditionExpression']
    response = table.put_item(**params )
    return response

  def getDynamodb(self):
    return self.dynamodb

  def query(self, table_name, kce=None, fe=None, index=None, limit=1):
    table = self.dynamodb.Table(table_name)
    params = {
      'IndexName': index,
      'Select': 'ALL_ATTRIBUTES',
      'ScanIndexForward': False,
      'KeyConditionExpression': kce,
      'FilterExpression':fe,
      'Limit': limit
    }
    if not index:
      del params['IndexName']
    if not kce:
      del params['KeyConditionExpression']
    if not fe:
      del params['FilterExpression']

    response = table.query(**params)
    return response

  def query_user_history(self, kce=None, fe=None):
    history = self.query("Access_Log", kce=kce, fe=fe, index="History_ID")
    return history

  def update_user_history(self, **kvargs):
    # overwrite allowed
    res = self.write_item("Access_Log", prevent_ow_attr=None, **kvargs)
    return res

  def query_photo(self, kce=None, fe=None):
    res = self.query("Pictures", kce=kce, fe=None, index="Photo_ID")
    return res

  def query_photo_history(self, kce=None, fe=None):
    res = self.query("Pictures", kce=kce, fe=fe, index="Photo_ID")
    return res
import code
class MySQL(object):
  def __init__(self):
    if os.environ['PYTHON_ENV'] == "development":
      url = os.environ['mysql_msgmeforpics']
    else:
      url = os.environ['JAWSDB_URL']

    url = urlparse.urlparse(url)

    self.db = MySQLdb.connect(
        host=url.hostname,
        user=url.username,
        passwd=url.password,
        db=url.path[1:]
      )
    self.cursor = self.db.cursor()

  def readOperation(self,query):
    try:
      self.cursor.execute(query)
      return self.cursor.fetchall()
    except Exception as e:
      # log
      logger.exception(str(e))
      return None

  def writeOperation(self,query, variables=()):
    try:
      # code.interact(local=dict(globals(), **locals()))
      self.cursor.execute(query, variables)
      self.db.commit()
      return True
    except Exception as e:
      #log
      logger.exception(str(e))
      self.db.rollback()
      return False

  def __del__(self):
    logger.warning("MySQL server connection closed")
    self.db.close()

  def cursor(self):
    return self.cursor