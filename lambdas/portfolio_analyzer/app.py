import json, logging, os, time
import boto3
logger = logging.getLogger(__name__)

class PortfolioAnalyzer:
    def __init__(self):
        from bedrock_client import get_bedrock_client
        from solana_client import get_solana_client
        self.bedrock = get_bedrock_client()
        self.solana = get_solana_client()
        self.positions_table = boto3.resource("dynamodb").Table(os.environ.get("POSITIONS_TABLE", "solanacfo-positions"))

    def handle(self, event):
        for rec in event.get("Records", []):
            try:
                body = json.loads(rec["body"])
                treasury_id = body.get("treasury_id", "")
                if treasury_id:
                    self.analyze_portfolio(treasury_id)
            except Exception as e:
                logger.error("Portfolio analysis error: %s", e)
        return {"statusCode": 200}

    def analyze_portfolio(self, treasury_id):
        positions = self.positions_table.query(KeyConditionExpression="treasury_id = :tid", ExpressionAttributeValues={":tid": treasury_id}).get("Items", [])
        on_chain_data = {}
        for pos in positions[:5]:
            wallet = pos.get("wallet_address", "")
            if wallet:
                try:
                    balance = self.solana.get_sol_balance(wallet)
                    on_chain_data[wallet] = {"sol_balance": balance}
                except Exception as e:
                    logger.warning("Failed to get balance for %s: %s", wallet, e)

        prompt = (
            f"Treasury ID: {treasury_id}
Positions: {len(positions)}
"
            f"On-chain data: {json.dumps(on_chain_data)}

"
            f"Analyze portfolio: concentration risk, DEX exposure, LP positions, overall health.
"
            f"JSON: {{positions_analysis, concentration_risk, dex_exposure, health_score, recommendations, confidence_score}}"
        )
        result = self.bedrock.invoke(prompt=prompt, system_prompt="You are a Portfolio Analyzer for Solana treasury management. Analyze on-chain positions and risks. JSON output with confidence scores.", temperature=0.2)
        logger.info("Portfolio analysis complete for %s", treasury_id)
        return result

def lambda_handler(event, context):
    return PortfolioAnalyzer().handle(event)
