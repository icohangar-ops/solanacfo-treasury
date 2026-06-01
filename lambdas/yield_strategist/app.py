import json, logging, os
import boto3
logger = logging.getLogger(__name__)

class YieldStrategist:
    def __init__(self):
        from bedrock_client import get_bedrock_client
        self.bedrock = get_bedrock_client()

    def handle(self, event):
        for rec in event.get("Records", []):
            try:
                body = json.loads(rec["body"])
                treasury_id = body.get("treasury_id", "")
                if treasury_id:
                    self.find_yield_opportunities(treasury_id, body)
            except Exception as e:
                logger.error("Yield strategist error: %s", e)
        return {"statusCode": 200}

    def find_yield_opportunities(self, treasury_id, data):
        current_positions = data.get("positions", [])
        risk_tolerance = data.get("risk_tolerance", "moderate")
        prompt = (
            f"Treasury: {treasury_id}, Risk Tolerance: {risk_tolerance}
"
            f"Current positions: {json.dumps(current_positions[:10], default=str)}

"
            f"Identify yield opportunities across Solana DeFi: lending, staking, LP farms, structured products.
"
            f"JSON: {{opportunities: [{name, protocol, apy, tvl, risk_rating, strategy}], confidence_score}}"
        )
        self.bedrock.invoke(prompt=prompt, system_prompt="You are a Yield Strategist for Solana treasuries. Find optimal yield opportunities. JSON output.", temperature=0.3)
        logger.info("Yield strategy complete for %s", treasury_id)

def lambda_handler(event, context):
    return YieldStrategist().handle(event)
