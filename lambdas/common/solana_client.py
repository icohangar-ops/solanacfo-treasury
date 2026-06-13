import json, logging, os, time
import urllib.error
import urllib.request

from cubiczan_resilience import resilient

logger = logging.getLogger(__name__)

# Transient failures worth retrying on a JSON-RPC endpoint: network/socket
# errors and HTTP-level errors (urllib raises HTTPError on 4xx/5xx). The
# @resilient decorator inspects the status code via the exception's .code /
# .response attributes and retries only on transient codes (429/5xx/...).
RETRYABLE_RPC_EXCEPTIONS = (urllib.error.URLError, OSError, TimeoutError)


class RpcError(RuntimeError):
    """Raised when the Solana RPC endpoint returns a JSON-RPC error payload."""


class SolanaClient:
    def __init__(self):
        self.rpc_url = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.timeout = int(os.environ.get("RPC_TIMEOUT", "30"))
        self.max_attempts = int(os.environ.get("RPC_MAX_ATTEMPTS", "3"))

    def _rpc(self, method, params):
        """Issue a single JSON-RPC POST with bounded retry + full-jitter backoff.

        Mirrors the retry posture of bedrock_client.py (3 attempts, exponential
        backoff). Network/transient HTTP failures are retried; a JSON-RPC error
        payload or exhausted retries propagate as exceptions rather than being
        masked by an empty default value.
        """

        @resilient(
            timeout=self.timeout,
            max_attempts=self.max_attempts,
            base_delay=0.5,
            retryable_exceptions=RETRYABLE_RPC_EXCEPTIONS,
        )
        def _call():
            payload = json.dumps(
                {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            ).encode()
            req = urllib.request.Request(
                self.rpc_url, data=payload, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode())
            if "error" in body:
                # Surface RPC-level errors instead of silently returning {}.
                raise RpcError(f"Solana RPC {method} error: {body['error']}")
            return body.get("result")

        return _call()

    def get_sol_balance(self, wallet_address):
        result = self._rpc("getBalance", [wallet_address])
        lamports = (result or {}).get("value", 0)
        return lamports / 1e9

    def get_token_accounts(self, wallet_address):
        result = self._rpc(
            "getTokenAccountsByOwner",
            [
                wallet_address,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"},
            ],
        )
        return (result or {}).get("value", [])

    def get_transaction_history(self, wallet_address, limit=10):
        result = self._rpc("getSignaturesForAddress", [wallet_address, {"limit": limit}])
        return result or []

    def get_account_info(self, wallet_address):
        result = self._rpc("getAccountInfo", [wallet_address])
        return result or {}


def get_solana_client():
    return SolanaClient()
