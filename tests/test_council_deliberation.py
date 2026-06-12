import pytest
class TestCouncil:
    def test_agent_count(self):
        agents = ['portfolio_analyzer', 'risk_monitor', 'yield_strategist', 'governance_analyst', 'treasury_cfo']
        assert len(agents) == 5