import json, logging, os, time
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
logger = logging.getLogger(__name__)

TABLE_PREFIX = os.environ.get("TABLE_PREFIX", "solanacfo-production")

class DynamoDBHelper:
    def __init__(self):
        self.resource = boto3.resource("dynamodb")
        self.tables = {
            "treasuries": self.resource.Table(f"{TABLE_PREFIX}-treasuries"),
            "positions": self.resource.Table(f"{TABLE_PREFIX}-positions"),
            "transactions": self.resource.Table(f"{TABLE_PREFIX}-transactions"),
            "deliberations": self.resource.Table(f"{TABLE_PREFIX}-deliberations"),
            "governance": self.resource.Table(f"{TABLE_PREFIX}-governance"),
            "alerts": self.resource.Table(f"{TABLE_PREFIX}-alerts"),
        }

    def put_item(self, table_name, item):
        table = self.tables.get(table_name)
        if table:
            table.put_item(Item=item)

    def get_item(self, table_name, key):
        table = self.tables.get(table_name)
        if table:
            return table.get_item(Key=key).get("Item")
        return None

def get_dynamodb_helper():
    return DynamoDBHelper()
