from typing import Any, Dict
from base_agent import BaseAgent
class RiskMonitorAgent(BaseAgent):
    def __init__(self, bedrock): super().__init__('risk_monitor', 'Risk Monitor', bedrock)
    def analyze(self, data): return self.invoke(f'Assess risks: {data}')
