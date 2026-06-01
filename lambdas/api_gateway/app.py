import json, logging, os
import boto3
from botocore.exceptions import ClientError
logger = logging.getLogger(__name__)
COGNITO = boto3.client("cognito-idp")
SQS = boto3.client("sqs")
DB = boto3.resource("dynamodb")

class APIGateway:
    def handle(self, event):
        method = event.get("httpMethod", "GET")
        path = event.get("path", "/")
        if path == "/health":
            return {"statusCode": 200, "body": json.dumps({"status": "healthy", "service": "solanacfo-treasury"})}
        auth = self._validate(event.get("headers", {}))
        if "error" in auth and path != "/health":
            return {"statusCode": 401, "body": json.dumps(auth)}
        body = json.loads(event.get("body", "{}") or "{}")
        queue = os.environ.get("DELIBERATION_QUEUE_URL", "")
        if queue and method == "POST":
            SQS.send_message(QueueUrl=queue, MessageBody=json.dumps(body))
            return {"statusCode": 202, "body": json.dumps({"accepted": True})}
        items = DB.Table(os.environ.get("TREASURIES_TABLE", "")).scan(Limit=50).get("Items", [])
        return {"statusCode": 200, "body": json.dumps({"treasuries": items})}

    def _validate(self, headers):
        auth = headers.get("authorization", "")
        if not auth.startswith("Bearer "): return {"error": "No auth"}
        try: COGNITO.get_user(AccessToken=auth.split(" ")[1]); return {"ok": True}
        except: return {"error": "Invalid"}

def lambda_handler(event, context):
    return APIGateway().handle(event)
