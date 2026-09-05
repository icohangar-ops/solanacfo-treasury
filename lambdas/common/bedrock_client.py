"""
Bedrock client for SolanaCFO Treasury.
Provides LLM invocation with streaming, fallback, and retry logic.
Uses Claude 3.5 Sonnet via Amazon Bedrock.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Generator, List, Optional

import boto3
from botocore.exceptions import ClientError, ConnectionError, ThrottlingException

from prism_observability import build_prism_telemetry, trace_llm as trace_prism_llm

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

_PRISM = build_prism_telemetry()

DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.0


class BedrockClient:
    """Amazon Bedrock client wrapper for Claude 3.5 Sonnet invocations."""

    def __init__(
        self,
        model_id: Optional[str] = None,
        region_name: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
        self.region_name = region_name or os.getenv("BEDROCK_REGION", "us-east-1")
        self.max_tokens = max_tokens
        self.temperature = temperature

        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region_name,
        )
        self.fallback_model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        logger.info(
            "BedrockClient initialized: model=%s, region=%s",
            self.model_id,
            self.region_name,
        )

    def _build_claude_request(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Build the request body for Claude model invocation."""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature or self.temperature,
        }

        if system_prompt:
            body["system"] = system_prompt

        if messages:
            body["messages"] = messages
        else:
            body["messages"] = [{"role": "user", "content": prompt}]

        return body

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        use_fallback: bool = True,
    ) -> Dict[str, Any]:
        """Invoke Claude model with retry and fallback logic.

        Args:
            prompt: User prompt text.
            system_prompt: System prompt for context.
            max_tokens: Override max tokens for this invocation.
            temperature: Override temperature for this invocation.
            messages: Pre-built messages array (bypasses prompt construction).
            use_fallback: Whether to use fallback model on failure.

        Returns:
            Dictionary with 'response', 'usage', 'model_id', 'latency_ms'.

        Raises:
            ClientError: If Bedrock invocation fails after all retries.
        """
        request_body = self._build_claude_request(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )

        last_error = None
        for attempt in range(MAX_RETRIES):
            model_id = self.model_id
            try:
                start_time = time.time()
                response = self.client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(request_body),
                    contentType="application/json",
                    accept="application/json",
                )
                latency_ms = int((time.time() - start_time) * 1000)

                response_body = json.loads(response["body"].read().decode("utf-8"))

                result = {
                    "response": response_body.get("content", [{}])[0].get("text", ""),
                    "usage": response_body.get("usage", {}),
                    "model_id": model_id,
                    "latency_ms": latency_ms,
                    "stop_reason": response_body.get("stop_reason", "end_turn"),
                    "attempt": attempt + 1,
                }

                trace_prism_llm(
                    _PRISM,
                    model=model_id,
                    input_messages=request_body.get("messages", []),
                    output=result["response"],
                    latency_ms=latency_ms,
                    token_count_input=int(result["usage"].get("input_tokens", 0) or 0),
                    token_count_output=int(result["usage"].get("output_tokens", 0) or 0),
                    metadata={
                    "source": "solanacfo-treasury",
                    "operation": "invoke",
                    "system_prompt": bool(system_prompt),
                    "fallback": self.model_id == self.fallback_model_id,
                },
            )

                logger.info(
                    "Bedrock invocation success: model=%s, latency=%dms, tokens_in=%d, tokens_out=%d",
                    model_id,
                    latency_ms,
                    result["usage"].get("input_tokens", 0),
                    result["usage"].get("output_tokens", 0),
                )
                return result

            except ThrottlingException as e:
                last_error = e
                backoff = RETRY_BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "Bedrock throttled, retrying in %.1fs (attempt %d/%d)",
                    backoff,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(backoff)

            except (ClientError, ConnectionError) as e:
                last_error = e
                error_code = getattr(e, "response", {}).get("Error", {}).get("Code", "Unknown")
                logger.error(
                    "Bedrock invocation error: %s (attempt %d/%d)",
                    error_code,
                    attempt + 1,
                    MAX_RETRIES,
                )
                if error_code in ("AccessDeniedException", "ValidationException"):
                    raise
                backoff = RETRY_BACKOFF_BASE * (2 ** attempt)
                time.sleep(backoff)

        if use_fallback and self.model_id != self.fallback_model_id:
            logger.warning(
                "Primary model failed, falling back to %s", self.fallback_model_id
            )
            fallback_client = BedrockClient(
                model_id=self.fallback_model_id,
                region_name=self.region_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            return fallback_client.invoke(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
                use_fallback=False,
            )

        raise last_error if last_error else ClientError(
            {"Error": {"Code": "InvocationFailed", "Message": "All retries exhausted"}},
            "invoke_model",
        )

    def invoke_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Generator[str, None, None]:
        """Invoke Claude model with streaming response.

        Args:
            prompt: User prompt text.
            system_prompt: System prompt for context.
            max_tokens: Override max tokens.
            temperature: Override temperature.

        Yields:
            Text chunks from the streaming response.
        """
        request_body = self._build_claude_request(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        try:
            start_time = time.time()
            output_chunks: list[str] = []
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )

            for event in response.get("body", []):
                chunk = event.get("chunk", {})
                if chunk:
                    data = json.loads(chunk.get("bytes", b"{}").decode("utf-8"))
                    content_blocks = data.get("content", [])
                    for block in content_blocks:
                        if block.get("type") == "text":
                            text = block.get("text", "")
                            if text:
                                output_chunks.append(text)
                                yield text

            trace_prism_llm(
                _PRISM,
                model=self.model_id,
                input_messages=request_body.get("messages", []),
                output="".join(output_chunks),
                latency_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "source": "solanacfo-treasury",
                    "operation": "invoke_streaming",
                },
            )

        except ClientError as e:
            logger.error("Bedrock streaming error: %s", str(e))
            raise

    def invoke_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Invoke Claude with JSON output expectations.

        Args:
            prompt: User prompt with instruction to return JSON.
            system_prompt: System prompt.
            response_schema: Optional JSON schema hint for the model.

        Returns:
            Parsed JSON response dictionary.
        """
        json_instruction = "\n\nYou must respond with valid JSON only. No markdown, no explanation outside JSON."
        enhanced_prompt = prompt + json_instruction

        if response_schema:
            schema_hint = f"\n\nThe response should conform to this JSON schema:\n{json.dumps(response_schema, indent=2)}"
            enhanced_prompt += schema_hint

        result = self.invoke(
            prompt=enhanced_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
        )

        try:
            response_text = result["response"].strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            return json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            logger.error("Failed to parse structured response: %s", str(e))
            return {
                "raw_response": result["response"],
                "parse_error": str(e),
            }

    def invoke_multi_turn(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Invoke Claude with multi-turn conversation messages.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            system_prompt: System prompt.
            max_tokens: Override max tokens.

        Returns:
            Invocation result dictionary.
        """
        validated_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role not in ("user", "assistant"):
                continue
            validated_messages.append({"role": role, "content": content})

        return self.invoke(
            prompt="",
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            messages=validated_messages,
        )


def get_bedrock_client() -> BedrockClient:
    """Factory function to create a BedrockClient instance."""
    return BedrockClient()
