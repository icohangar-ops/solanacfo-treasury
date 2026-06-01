import json, logging, os, time
import boto3
import urllib.request
logger = logging.getLogger(__name__)

class SolanaClient:
    def __init__(self):
        self.rpc_url = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.timeout = int(os.environ.get("RPC_TIMEOUT", "30"))

    def get_sol_balance(self, wallet_address):
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [wallet_address]}).encode()
        req = urllib.request.Request(self.rpc_url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            result = json.loads(resp.read().decode())
            lamports = result.get("result", {}).get("value", 0)
            return lamports / 1e9

    def get_token_accounts(self, wallet_address):
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner", "params": [wallet_address, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}]}).encode()
        req = urllib.request.Request(self.rpc_url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode()).get("result", {}).get("value", [])

    def get_transaction_history(self, wallet_address, limit=10):
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": [wallet_address, {"limit": limit}]}).encode()
        req = urllib.request.Request(self.rpc_url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode()).get("result", [])

    def get_account_info(self, wallet_address):
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getAccountInfo", "params": [wallet_address]}).encode()
        req = urllib.request.Request(self.rpc_url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode()).get("result", {})

def get_solana_client():
    return SolanaClient()
