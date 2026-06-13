"""Money/math characterization + edge-case tests for DefiAnalytics.

These cover the pure financial math on the treasury critical path:
  - impermanent loss (LP exposure)
  - APY estimation (yield)
  - liquidation risk / LTV thresholds

Expected values are derived directly from the closed-form formulas, so a
regression in the arithmetic (sign flip, wrong divisor, dropped *100, bad
threshold comparison) will fail these tests rather than silently mispricing.
"""
import math
import os
import sys

import pytest

# The lambda modules import sibling files by bare name (no package), so put the
# common dir on sys.path the same way the Lambda runtime does.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lambdas", "common"),
)

from defi_analytics import DefiAnalytics, get_defi_analytics  # noqa: E402


@pytest.fixture
def analytics():
    return DefiAnalytics()


# ---------------------------------------------------------------------------
# Impermanent loss:  il = | 2 * sqrt(r)/(1+r) - 1 | * 100,  r = ratio_cur/ratio_init
# ---------------------------------------------------------------------------

def test_il_no_price_change_is_zero(analytics):
    # Prices unchanged -> r == 1 -> IL must be exactly 0.
    assert analytics.calculate_impermanent_loss(100, 100, 50, 50) == 0.0


def test_il_2x_relative_move_is_canonical_5_72(analytics):
    # Token A doubles relative to B (ratio 1 -> 2). The textbook IL for a 2x
    # relative move is ~5.72%. Compute from formula to avoid magic numbers.
    r = 2.0
    expected = round(abs(2 * (math.sqrt(r) / (1 + r)) - 1) * 100, 2)
    assert expected == 5.72  # guards the formula constant itself
    got = analytics.calculate_impermanent_loss(
        token_a_price_initial=100,
        token_a_price_current=200,
        token_b_price_initial=100,
        token_b_price_current=100,
    )
    assert got == 5.72


def test_il_4x_move_matches_formula(analytics):
    # ratio 1 -> 4. Known canonical IL for 4x is ~20.0%.
    got = analytics.calculate_impermanent_loss(100, 400, 100, 100)
    r = 4.0
    expected = round(abs(2 * (math.sqrt(r) / (1 + r)) - 1) * 100, 2)
    assert expected == 20.0
    assert got == 20.0


def test_il_is_symmetric_for_inverse_move(analytics):
    # A halving vs B (ratio 1 -> 0.5) gives the same IL as a doubling because
    # the function takes abs(). Regression guard against asymmetric handling.
    up = analytics.calculate_impermanent_loss(100, 200, 100, 100)
    down = analytics.calculate_impermanent_loss(100, 50, 100, 100)
    assert up == down == 5.72


def test_il_zero_denominator_price_b_defaults_to_neutral(analytics):
    # token_b_price_initial == 0 makes price_ratio_initial fall back to 1.
    # With current ratio also forced (b_current==0 -> 1), r == 1 -> IL 0.
    assert analytics.calculate_impermanent_loss(100, 200, 0, 0) == 0.0


# ---------------------------------------------------------------------------
# APY:  base = fees_30d * 12 / tvl * 100 ; result = round(base + reward, 2)
# ---------------------------------------------------------------------------

def test_apy_known_input(analytics):
    # 1000 fees/30d * 12 = 12000 annual; /100000 * 100 = 12%; + 3 reward = 15.
    assert analytics.estimate_apy(tvl=100_000, fees_30d=1000, reward_rate=3) == 15.0


def test_apy_without_reward(analytics):
    assert analytics.estimate_apy(tvl=100_000, fees_30d=1000) == 12.0


def test_apy_zero_tvl_returns_reward_only(analytics):
    # Division guard: tvl <= 0 -> base 0, so only the reward rate remains.
    assert analytics.estimate_apy(tvl=0, fees_30d=5000, reward_rate=4) == 4.0


def test_apy_negative_tvl_does_not_divide(analytics):
    # Negative TVL is nonsensical; the `tvl > 0` guard must prevent a negative
    # APY blowup. Characterizes current behavior: base suppressed to 0.
    assert analytics.estimate_apy(tvl=-100, fees_30d=1000, reward_rate=2) == 2.0


def test_apy_no_fees_no_reward_is_zero(analytics):
    assert analytics.estimate_apy(tvl=100_000, fees_30d=0) == 0.0


# ---------------------------------------------------------------------------
# Liquidation risk:  ltv = borrow/collateral ; risk = ltv/threshold * 100
#   level: >80 high, >50 medium, else low ; risk_pct capped at 100
# ---------------------------------------------------------------------------

def test_liquidation_low_risk(analytics):
    out = analytics.assess_liquidation_risk(collateral_value=10_000, borrow_value=4_000)
    assert out["ltv"] == 0.4
    assert out["risk_pct"] == 50.0  # 0.4 / 0.8 * 100
    assert out["level"] == "low"  # 50 is NOT > 50 -> stays low


def test_liquidation_medium_risk_boundary(analytics):
    # borrow 4400 -> ltv 0.44 -> risk 55 -> medium (just over the 50 line).
    out = analytics.assess_liquidation_risk(collateral_value=10_000, borrow_value=4_400)
    assert out["ltv"] == 0.44
    assert out["risk_pct"] == 55.0
    assert out["level"] == "medium"


def test_liquidation_high_risk(analytics):
    out = analytics.assess_liquidation_risk(collateral_value=10_000, borrow_value=7_000)
    assert out["ltv"] == 0.7
    assert out["risk_pct"] == 87.5
    assert out["level"] == "high"


def test_liquidation_risk_pct_capped_at_100_but_level_uses_raw(analytics):
    # borrow 9000 -> ltv 0.9 -> raw risk 112.5 -> displayed risk capped at 100,
    # but level is derived from the uncapped value so it must still be "high".
    out = analytics.assess_liquidation_risk(collateral_value=10_000, borrow_value=9_000)
    assert out["ltv"] == 0.9
    assert out["risk_pct"] == 100.0  # capped
    assert out["level"] == "high"


def test_liquidation_custom_threshold(analytics):
    # Tighter threshold (0.5) makes the same position riskier.
    out = analytics.assess_liquidation_risk(
        collateral_value=10_000, borrow_value=4_000, ltv_threshold=0.5
    )
    assert out["ltv"] == 0.4
    assert out["risk_pct"] == 80.0  # 0.4 / 0.5 * 100
    assert out["level"] == "medium"  # 80 is not > 80


def test_liquidation_zero_collateral_is_treated_as_low(analytics):
    # KNOWN LATENT EDGE: zero collateral with outstanding debt divides to ltv 0
    # and reports "low", which understates a fully-undercollateralized position.
    # Pinned as characterization so any future change to this behavior is
    # deliberate and visible in the diff.
    out = analytics.assess_liquidation_risk(collateral_value=0, borrow_value=5_000)
    assert out["ltv"] == 0
    assert out["risk_pct"] == 0
    assert out["level"] == "low"


def test_liquidation_no_debt(analytics):
    out = analytics.assess_liquidation_risk(collateral_value=10_000, borrow_value=0)
    assert out["ltv"] == 0.0
    assert out["risk_pct"] == 0.0
    assert out["level"] == "low"


def test_factory_returns_instance():
    assert isinstance(get_defi_analytics(), DefiAnalytics)
