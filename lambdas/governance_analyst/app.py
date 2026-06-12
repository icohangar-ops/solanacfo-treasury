import json, logging, os
import boto3
logger = logging.getLogger(__name__)

class GovernanceAnalyst:
    def __init__(self):
        from bedrock_client import get_bedrock_client
        self.bedrock = get_bedrock_client()

    def handle(self, event):
        for rec in event.get("Records", []):
            try:
                body = json.loads(rec["body"])
                treasury_id = body.get("treasury_id", "")
                if treasury_id:
                    self.analyze_governance(treasury_id, body)
            except Exception as e:
                logger.error("Governance analyst error: %s", e)
        return {"statusCode": 200}

    def analyze_governance(self, treasury_id, data):
        proposals = data.get("proposals", [])
        prompt = (
            f"Treasury: {treasury_id}\nProposals: {json.dumps(proposals[:5], default=str)}\n\n"
            f"Analyze DAO proposals: token voting patterns, delegation analysis, alignment with treasury goals.\n"
            f"JSON: {{proposal_analyses, voting_recommendations, alignment_scores, confidence_score}}"
        )
        self.bedrock.invoke(prompt=prompt, system_prompt="You are a Governance Analyst for Solana DAOs. Analyze proposals and voting. JSON output.", temperature=0.3)
        logger.info("Governance analysis complete for %s", treasury_id)

def lambda_handler(event, context):
    return GovernanceAnalyst().handle(event)
