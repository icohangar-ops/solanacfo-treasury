"""
Deepgram client for SolanaCFO Treasury.
Provides Speech-to-Text (Nova-2) and Text-to-Speech (Aura) integrations
for voice briefings and voice commands.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional

import boto3
import requests
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

DEEPGRAM_BASE_URL = "https://api.deepgram.com/v2"
NOVA_2_MODEL = "nova-2"
AURA_MODEL = "aura-asteria-en"


class DeepgramClient:
    """Deepgram API client for STT/TTS operations."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY", "")
        self.base_url = base_url or DEEPGRAM_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        })
        self.s3_client = boto3.client("s3")
        self.s3_bucket = os.getenv("S3_AUDIO_BRIEFINGS_BUCKET", "")
        logger.info("DeepgramClient initialized")

    def transcribe_audio(
        self,
        audio_data: bytes,
        content_type: str = "audio/wav",
        language: str = "en",
        smart_format: bool = True,
        detect_topics: bool = True,
        detect_sentiment: bool = True,
    ) -> Dict[str, Any]:
        """Transcribe audio to text using Nova-2 model.

        Args:
            audio_data: Raw audio bytes.
            content_type: MIME type of the audio.
            language: Language code (default: 'en').
            smart_format: Whether to use Smart Format for readability.
            detect_topics: Whether to detect topics.
            detect_sentiment: Whether to detect sentiment.

        Returns:
            Transcription result with text, confidence, words, topics, sentiment.
        """
        url = f"{self.base_url}/listen"
        params = {
            "model": NOVA_2_MODEL,
            "language": language,
            "smart_format": str(smart_format).lower(),
            "detect_topics": str(detect_topics).lower(),
            "detect_sentiment": str(detect_sentiment).lower(),
            "punctuate": "true",
            "utterances": "true",
            "diarize": "false",
            "ner": "true",
        }

        headers = {
            "Content-Type": content_type,
        }

        try:
            response = self.session.post(
                url,
                params=params,
                headers=headers,
                data=audio_data,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            transcription = {
                "text": result.get("results", {}).get("channels", [{}])[0]
                .get("alternatives", [{}])[0]
                .get("transcript", ""),
                "confidence": result.get("results", {}).get("channels", [{}])[0]
                .get("alternatives", [{}])[0]
                .get("confidence", 0.0),
                "words": result.get("results", {}).get("channels", [{}])[0]
                .get("alternatives", [{}])[0]
                .get("words", []),
                "utterances": result.get("results", {}).get("utterances", []),
                "duration": result.get("duration", 0.0),
                "topics": self._extract_topics(result),
                "sentiment": self._extract_sentiment(result),
            }

            logger.info(
                "Transcription complete: %d chars, confidence=%.2f, duration=%.1fs",
                len(transcription["text"]),
                transcription["confidence"],
                transcription["duration"],
            )
            return transcription

        except requests.RequestException as e:
            logger.error("Deepgram STT error: %s", str(e))
            raise RuntimeError(f"Transcription failed: {str(e)}") from e

    def transcribe_from_s3(
        self,
        s3_key: str,
        bucket: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Transcribe an audio file from S3.

        Args:
            s3_key: S3 object key for the audio file.
            bucket: Override bucket name.

        Returns:
            Transcription result.
        """
        target_bucket = bucket or self.s3_bucket
        try:
            response = self.s3_client.get_object(Bucket=target_bucket, Key=s3_key)
            audio_data = response["Body"].read()
            content_type = response.get("ContentType", "audio/wav")

            return self.transcribe_audio(audio_data, content_type=content_type)
        except ClientError as e:
            logger.error("Failed to fetch audio from S3: %s", str(e))
            raise

    def synthesize_speech(
        self,
        text: str,
        model: str = AURA_MODEL,
        encoding: str = "mp3",
        sample_rate: int = 24000,
        voice_speed: Optional[float] = None,
    ) -> bytes:
        """Synthesize speech from text using Aura TTS model.

        Args:
            text: Text to convert to speech.
            model: TTS model name.
            encoding: Audio encoding (mp3, wav, pcm).
            sample_rate: Sample rate in Hz.
            voice_speed: Playback speed multiplier (0.5 to 2.0).

        Returns:
            Raw audio bytes.
        """
        url = f"{self.base_url}/speak"
        params = {
            "model": model,
            "encoding": encoding,
            "sample_rate": str(sample_rate),
        }
        if voice_speed:
            params["speed"] = str(voice_speed)

        payload = {"text": text}

        try:
            response = self.session.post(
                url,
                params=params,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()

            audio_bytes = response.content
            logger.info(
                "TTS synthesis complete: %d bytes, encoding=%s, model=%s",
                len(audio_bytes),
                encoding,
                model,
            )
            return audio_bytes

        except requests.RequestException as e:
            logger.error("Deepgram TTS error: %s", str(e))
            raise RuntimeError(f"TTS synthesis failed: {str(e)}") from e

    def generate_briefing_audio(
        self,
        briefing_text: str,
        briefing_id: str,
        bucket: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate an audio briefing from text and upload to S3.

        Args:
            briefing_text: Treasury briefing text to convert to speech.
            briefing_id: Unique identifier for the briefing.
            bucket: Override S3 bucket.

        Returns:
            Dictionary with s3_key, size, content_type, generation_time_ms.
        """
        start_time = time.time()

        audio_bytes = self.synthesize_speech(briefing_text)

        target_bucket = bucket or self.s3_bucket
        timestamp = int(time.time())
        s3_key = f"briefings/{briefing_id}/{timestamp}_briefing.mp3"

        self.s3_client.put_object(
            Bucket=target_bucket,
            Key=s3_key,
            Body=audio_bytes,
            ContentType="audio/mpeg",
            Metadata={
                "briefing_id": briefing_id,
                "model": AURA_MODEL,
                "timestamp": str(timestamp),
            },
        )

        generation_time_ms = int((time.time() - start_time) * 1000)

        result = {
            "s3_bucket": target_bucket,
            "s3_key": s3_key,
            "size_bytes": len(audio_bytes),
            "content_type": "audio/mpeg",
            "model": AURA_MODEL,
            "generation_time_ms": generation_time_ms,
            "briefing_id": briefing_id,
        }

        logger.info(
            "Briefing audio generated: key=%s, size=%d bytes, time=%dms",
            s3_key,
            len(audio_bytes),
            generation_time_ms,
        )
        return result

    def get_presigned_url(
        self,
        s3_key: str,
        bucket: Optional[str] = None,
        expires_in: int = 3600,
    ) -> str:
        """Generate a presigned URL for accessing a briefing audio file.

        Args:
            s3_key: S3 object key.
            bucket: Override bucket name.
            expires_in: URL expiration in seconds.

        Returns:
            Presigned URL string.
        """
        target_bucket = bucket or self.s3_bucket
        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": target_bucket, "Key": s3_key},
            ExpiresIn=expires_in,
        )

    def _extract_topics(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract detected topics from transcription result."""
        topics = []
        try:
            topics_data = result.get("results", {}).get("topics", {}).get("segments", [])
            for segment in topics_data:
                topics.append({
                    "text": segment.get("text", ""),
                    "topics": segment.get("topics", []),
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                })
        except (KeyError, TypeError, AttributeError):
            pass
        return topics

    def _extract_sentiment(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract sentiment analysis from transcription result."""
        sentiment = {"overall": "neutral", "average_confidence": 0.0, "segments": []}
        try:
            sentiment_data = result.get("results", {}).get("sentiments", {}).get("segments", [])
            sentiments = []
            for segment in sentiment_data:
                sentiments.append({
                    "text": segment.get("text", ""),
                    "sentiment": segment.get("sentiment", "neutral"),
                    "confidence": segment.get("confidence", 0.0),
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                })

            if sentiments:
                positive_count = sum(1 for s in sentiments if s["sentiment"] == "positive")
                negative_count = sum(1 for s in sentiments if s["sentiment"] == "negative")
                if positive_count > negative_count:
                    sentiment["overall"] = "positive"
                elif negative_count > positive_count:
                    sentiment["overall"] = "negative"
                sentiment["average_confidence"] = (
                    sum(s["confidence"] for s in sentiments) / len(sentiments)
                )
                sentiment["segments"] = sentiments
        except (KeyError, TypeError, AttributeError):
            pass
        return sentiment


def get_deepgram_client() -> DeepgramClient:
    """Factory function to create a DeepgramClient instance."""
    return DeepgramClient()
