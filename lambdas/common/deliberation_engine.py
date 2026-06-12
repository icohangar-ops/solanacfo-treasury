import json, logging, os
from bedrock_client import get_bedrock_client
logger = logging.getLogger(__name__)

AGENT_ROLES = ["portfolio_analyzer", "risk_monitor", "yield_strategist", "governance_analyst", "treasury_cfo"]

class TreasuryDeliberationEngine:
    def __init__(self):
        self.bedrock = get_bedrock_client()

    def run(self, treasury_id, context):
        contributions = []
        for role in AGENT_ROLES:
            try:
                prompt = (
                    f"Treasury: {treasury_id}\n"
                    f"As the {role.replace('_', ' ').title()}, analyze: {json.dumps(context, default=str)[:2000]}\n"
                    f"JSON: {{analysis, risk_level, recommendations, confidence_score}}"
                )
                result = self.bedrock.invoke(prompt=prompt, temperature=0.3)
                contributions.append({"agent": role, "result": result})
            except Exception as e:
                contributions.append({"agent": role, "error": str(e)})
        synthesis_prompt = f"Synthesize {len(contributions)} agent analyses for treasury {treasury_id}. JSON: {{recommendation, confidence, action_items}}"
        synthesis = self.bedrock.invoke(prompt=synthesis_prompt, temperature=0.2)
        return {"contributions": contributions, "synthesis": synthesis}

def get_deliberation_engine():
    return TreasuryDeliberationEngine()
