import json, logging, os
import boto3
logger = logging.getLogger(__name__)

class TreasuryCFO:
    def __init__(self):
        from bedrock_client import get_bedrock_client
        self.bedrock = get_bedrock_client()

    def handle(self, event):
        for rec in event.get("Records", []):
            try:
                body = json.loads(rec["body"])
                treasury_id = body.get("treasury_id", "")
                if treasury_id:
                    self.cfo_analysis(treasury_id, body)
            except Exception as e:
                logger.error("Treasury CFO error: %s", e)
        return {"statusCode": 200}

    def cfo_analysis(self, treasury_id, data):
        prompt = (
            f"Treasury: {treasury_id}\nData: {json.dumps(data, default=str)[:3000]}\n\n"
            f"Overall treasury health: cash flow, rebalancing needs, risk-adjusted returns.\n"
            f"JSON: {{treasury_health, rebalancing_recommendations, risk_adjusted_returns, health_score, confidence_score}}"
        )
        self.bedrock.invoke(prompt=prompt, system_prompt="You are the Treasury CFO for Solana treasuries. Overall health assessment and strategic recommendations. JSON output.", temperature=0.2)
        logger.info("Treasury CFO analysis complete for %s", treasury_id)

def lambda_handler(event, context):
    return TreasuryCFO().handle(event)
