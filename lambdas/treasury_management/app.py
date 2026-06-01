import json, logging, os, uuid, time
import boto3
from botocore.exceptions import ClientError
logger = logging.getLogger(__name__)
DB = boto3.resource("dynamodb")

class TreasuryManager:
    def __init__(self):
        self.table = DB.Table(os.environ.get("TREASURIES_TABLE", "solanacfo-treasuries"))
        self.positions_table = DB.Table(os.environ.get("POSITIONS_TABLE", "solanacfo-positions"))

    def handle(self, event):
        for rec in event.get("Records", []):
            try:
                body = json.loads(rec["body"])
                action = body.get("action", "create")
                if action == "create":
                    self.create_treasury(body.get("data", {}), body.get("user", {}))
            except Exception as e:
                logger.error("Treasury mgmt error: %s", e)
        return {"statusCode": 200}

    def create_treasury(self, data, user):
        treasury_id = f"trs-{uuid.uuid4().hex[:10]}"
        now = time.strftime("%%Y-%%m-%%dT%%H:%%M:%%SZ", time.gmtime())
        item = {
            "treasury_id": treasury_id, "name": data.get("name", ""),
            "wallet_addresses": data.get("wallet_addresses", []),
            "total_value_usd": 0.0, "sol_balance": 0.0, "usdc_balance": 0.0,
            "allocation_targets": data.get("allocation_targets", {}),
            "risk_tolerance": data.get("risk_tolerance", "moderate"),
            "created_by": user.get("username", "system"), "status": "active",
            "created_at": now, "updated_at": now, "health_score": 1.0,
        }
        self.table.put_item(Item=item)
        logger.info("Treasury created: %s", treasury_id)
        return item

def lambda_handler(event, context):
    return TreasuryManager().handle(event)
