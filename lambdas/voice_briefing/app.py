import json, logging, os, time
import boto3
logger = logging.getLogger(__name__)

class VoiceBriefing:
    def __init__(self):
        from deepgram_client import get_deepgram_client
        self.deepgram = get_deepgram_client()
        self.db = boto3.resource("dynamodb")

    def handle(self, event):
        for rec in event.get("Records", []):
            try:
                body = json.loads(rec["body"])
                treasury_id = body.get("treasury_id", "")
                if treasury_id:
                    self.generate_briefing(treasury_id)
            except Exception as e:
                logger.error("Voice briefing error: %s", e)
        return {"statusCode": 200}

    def generate_briefing(self, treasury_id):
        table = self.db.Table(os.environ.get("TREASURIES_TABLE", "solanacfo-treasuries"))
        treasury = table.get_item(Key={"treasury_id": treasury_id}).get("Item")
        if not treasury:
            return
        script = (
            f"SolanaCFO Treasury Briefing for {treasury.get('name', 'Treasury')}. "
            f"Total value: {treasury.get('total_value_usd', 0):,.2f} USD. "
            f"SOL balance: {treasury.get('sol_balance', 0):,.4f}. "
            f"USDC balance: {treasury.get('usdc_balance', 0):,.2f}. "
            f"Health score: {treasury.get('health_score', 0):.2f}. "
            f"Risk tolerance: {treasury.get('risk_tolerance', 'moderate')}."
        )
        audio = self.deepgram.text_to_speech(script)
        logger.info("Voice briefing generated for %s", treasury_id)
        return {"treasury_id": treasury_id, "script_length": len(script)}

def lambda_handler(event, context):
    return VoiceBriefing().handle(event)
