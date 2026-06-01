from typing import Any, Dict
from base_agent import BaseAgent
class PortfolioAnalyzerAgent(BaseAgent):
    def __init__(self, bedrock): super().__init__('portfolio_analyzer', 'Portfolio Analyzer', bedrock)
    def analyze(self, data): return self.invoke(f'Analyze portfolio: {data}')
