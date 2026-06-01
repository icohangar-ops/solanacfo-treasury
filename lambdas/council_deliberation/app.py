import json, logging, os, uuid, time
import boto3
logger = logging.getLogger(__name__)

class CouncilDeliberation:
    def __init__(self):
        from bedrock_client import get_bedrock_client
        self.bedrock = get_bedrock_client()
        self.db = boto3.resource("dynamodb")

    def handle(self, event):
        for rec in event.get("Records", []):
            try:
                body = json.loads(rec["body"])
                treasury_id = body.get("treasury_id", "")
                if treasury_id:
                    self.deliberate(treasury_id, body)
            except Exception as e:
                logger.error("Council deliberation error: %s", e)
        return {"statusCode": 200}

    def deliberate(self, treasury_id, data):
        agents = ["portfolio_analyzer", "risk_monitor", "yield_strategist", "governance_analyst", "treasury_cfo"]
        contributions = []
        for agent in agents:
            try:
                prompt = (
                    f"Treasury: {treasury_id}
Context: {json.dumps(data, default=str)[:2000]}
"
                    f"As the {agent.replace('_', ' ').title()}, provide your analysis.
"
                    f"JSON: {{analysis, risk_level, recommendations, confidence_score}}"
                )
                result = self.bedrock.invoke(prompt=prompt, temperature=0.3)
                contributions.append({"agent": agent, "result": result})
            except Exception as e:
                contributions.append({"agent": agent, "error": str(e)})

        synthesis_prompt = (
            f"Treasury: {treasury_id}
Agent Contributions: {json.dumps(contributions, default=str)[:3000]}
"
            f"Synthesize into final treasury management recommendation.
"
            f"JSON: {{recommendation, confidence, action_items, risk_assessment, allocation_changes}}"
        )
        synthesis = self.bedrock.invoke(prompt=synthesis_prompt, system_prompt="You are the Council Synthesizer for Solana treasury management. JSON output.", temperature=0.2)

        logger.info("Council deliberation complete for %s", treasury_id)
        return {"treasury_id": treasury_id, "synthesis": synthesis, "contributions": contributions}

def lambda_handler(event, context):
    return CouncilDeliberation().handle(event)
