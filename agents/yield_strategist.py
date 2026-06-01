from typing import Any, Dict
from base_agent import BaseAgent
class YieldStrategistAgent(BaseAgent):
    def __init__(self, bedrock): super().__init__('yield_strategist', 'Yield Strategist', bedrock)
    def analyze(self, data): return self.invoke(f'Find yields: {data}')
