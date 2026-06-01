import json, logging, os
import boto3
logger = logging.getLogger(__name__)

class RiskMonitor:
    def __init__(self):
        from bedrock_client import get_bedrock_client
        self.bedrock = get_bedrock_client()

    def handle(self, event):
        for rec in event.get("Records", []):
            try:
                body = json.loads(rec["body"])
                treasury_id = body.get("treasury_id", "")
                if treasury_id:
                    self.monitor_risks(treasury_id, body)
            except Exception as e:
                logger.error("Risk monitor error: %s", e)
        return {"statusCode": 200}

    def monitor_risks(self, treasury_id, data):
        positions = data.get("positions", [])
        portfolio_value = sum(p.get("value_usd", 0) for p in positions)
        prompt = (
            f"Treasury: {treasury_id}, Value: ${portfolio_value:,.0f}
"
            f"Positions: {json.dumps(positions[:10], default=str)}

"
            f"Assess risks: price exposure, liquidation risk, smart contract risk, impermanent loss.
"
            f"JSON: {{risk_matrix, liquidation_risks, impermanent_loss, contract_risks, overall_risk_level, confidence_score}}"
        )
        self.bedrock.invoke(prompt=prompt, system_prompt="You are a Risk Monitor for Solana treasuries. Assess DeFi and on-chain risks. JSON output.", temperature=0.2)
        logger.info("Risk monitoring complete for %s", treasury_id)

def lambda_handler(event, context):
    return RiskMonitor().handle(event)
