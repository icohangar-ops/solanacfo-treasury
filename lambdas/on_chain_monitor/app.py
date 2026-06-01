import json, logging, os, time
import boto3
logger = logging.getLogger(__name__)

class OnChainMonitor:
    def __init__(self):
        from solana_client import get_solana_client
        self.solana = get_solana_client()
        self.sns = boto3.client("sns")
        self.alerts_table = boto3.resource("dynamodb").Table(os.environ.get("RISK_ALERTS_TABLE", "solanacfo-alerts"))

    def handle(self, event):
        for rec in event.get("Records", []):
            try:
                body = json.loads(rec["body"])
                self.process_event(body)
            except Exception as e:
                logger.error("On-chain monitor error: %s", e)
        return {"statusCode": 200}

    def process_event(self, data):
        event_type = data.get("event_type", "transfer")
        treasury_id = data.get("treasury_id", "")
        amount = float(data.get("amount", 0))
        threshold = float(data.get("threshold", 5))

        if event_type == "large_transfer" and amount > threshold:
            alert = {
                "alert_id": f"alt-{int(time.time())}", "treasury_id": treasury_id,
                "event_type": event_type, "amount": amount, "severity": "high",
                "message": f"Large transfer detected: {amount} SOL",
                "created_at": time.strftime("%%Y-%%m-%%dT%%H:%%M:%%SZ", time.gmtime()),
            }
            self.alerts_table.put_item(Item=alert)
            topic = os.environ.get("PRICE_ALERTS_TOPIC_ARN", "")
            if topic:
                self.sns.publish(TopicArn=topic, Subject=f"SolanaCFO Alert: Large Transfer", Message=json.dumps(alert, default=str))
            logger.warning("Alert: large transfer %s SOL for treasury %s", amount, treasury_id)

def lambda_handler(event, context):
    return OnChainMonitor().handle(event)
