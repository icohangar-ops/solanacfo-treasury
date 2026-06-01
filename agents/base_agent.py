from abc import ABC, abstractmethod
from typing import Any, Dict
class BaseAgent(ABC):
    def __init__(self, agent_id, agent_name, bedrock_client):
        self.agent_id, self.agent_name, self.bedrock = agent_id, agent_name, bedrock_client
    @abstractmethod
    def analyze(self, data) -> Dict[str, Any]: pass
    def invoke(self, prompt):
        return self.bedrock.invoke(prompt=prompt, max_tokens=4096, temperature=0.3)
