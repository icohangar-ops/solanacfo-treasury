import json, logging, os
logger = logging.getLogger(__name__)

class DefiAnalytics:
    def __init__(self):
        self.rpc_url = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

    def calculate_impermanent_loss(self, token_a_price_initial, token_a_price_current, token_b_price_initial, token_b_price_current):
        price_ratio_initial = token_a_price_initial / token_b_price_initial if token_b_price_initial else 1
        price_ratio_current = token_a_price_current / token_b_price_current if token_b_price_current else 1
        if price_ratio_initial == 0: return 0
        ratio_change = price_ratio_current / price_ratio_initial
        il_pct = 2 * (ratio_change ** 0.5 / (1 + ratio_change)) - 1
        return round(abs(il_pct) * 100, 2)

    def estimate_apy(self, tvl, fees_30d, reward_rate=0):
        annual_fees = fees_30d * 12
        base_apy = (annual_fees / tvl * 100) if tvl > 0 else 0
        return round(base_apy + reward_rate, 2)

    def assess_liquidation_risk(self, collateral_value, borrow_value, ltv_threshold=0.8):
        ltv = borrow_value / collateral_value if collateral_value > 0 else 0
        risk_pct = (ltv / ltv_threshold) * 100 if ltv_threshold > 0 else 0
        return {"ltv": round(ltv, 4), "risk_pct": round(min(risk_pct, 100), 2), "level": "high" if risk_pct > 80 else "medium" if risk_pct > 50 else "low"}

def get_defi_analytics():
    return DefiAnalytics()
