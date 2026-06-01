import json, logging, os, time
import boto3
logger = logging.getLogger(__name__)

class GovernanceExecutor:
    def __init__(self):
        from solana_client import get_solana_client
        from spl_operations import get_spl_client
        self.solana = get_solana_client()
        self.spl = get_spl_client()
        self.table = boto3.resource("dynamodb").Table(os.environ.get("GOVERNANCE_TABLE", "solanacfo-governance"))

    def handle(self, event):
        for rec in event.get("Records", []):
            try:
                body = json.loads(rec["body"])
                action = body.get("action", "create_proposal")
                if action == "create_proposal":
                    self.create_proposal(body)
                elif action == "execute_proposal":
                    self.execute_proposal(body)
            except Exception as e:
                logger.error("Governance executor error: %s", e)
        return {"statusCode": 200}

    def create_proposal(self, data):
        proposal_id = f"gov-{int(time.time())}"
        item = {
            "proposal_id": proposal_id, "treasury_id": data.get("treasury_id", ""),
            "title": data.get("title", ""), "description": data.get("description", ""),
            "proposal_type": data.get("type", "treasury_allocation"),
            "votes_for": 0, "votes_against": 0, "status": "active",
            "created_at": time.strftime("%%Y-%%m-%%dT%%H:%%M:%%SZ", time.gmtime()),
            "quorum_required": data.get("quorum_required", 0.6),
        }
        self.table.put_item(Item=item)
        logger.info("Governance proposal created: %s", proposal_id)
        return item

    def execute_proposal(self, data):
        proposal_id = data.get("proposal_id", "")
        proposal = self.table.get_item(Key={"proposal_id": proposal_id}).get("Item")
        if not proposal:
            return {"error": "Proposal not found"}
        total = proposal.get("votes_for", 0) + proposal.get("votes_against", 0)
        quorum = proposal.get("votes_for", 0) / total if total > 0 else 0
        if quorum >= proposal.get("quorum_required", 0.6):
            self.table.update_item(Key={"proposal_id": proposal_id},
                UpdateExpression="SET #status = :s", ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":s": "executed"})
            logger.info("Proposal %s executed with %.0f%% support", proposal_id, quorum * 100)
        return {"proposal_id": proposal_id, "quorum": quorum, "executed": quorum >= proposal.get("quorum_required", 0.6)}

def lambda_handler(event, context):
    return GovernanceExecutor().handle(event)
