"""
Fluid AI — LLM Client
Handles all communication with the Groq API (Llama 3.3 70B).
Includes retry logic with exponential backoff for resilience.
"""

from __future__ import annotations

import json
import time
import logging
import re
from typing import Optional

from groq import Groq, APIError, RateLimitError, APIConnectionError

from config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TEMPERATURE,
    GROQ_MAX_TOKENS,
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
)

logger = logging.getLogger("fluid_ai.llm")


class LLMClient:
    """
    Wrapper around the Groq API with built-in retry logic.
    
    Features:
    - Exponential backoff on transient failures
    - Structured JSON output parsing
    - Detailed logging for debugging
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        import os
        self.api_key = api_key or os.getenv("GROQ_API_KEY", GROQ_API_KEY)
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com "
                "and set it in your .env file or UI."
            )
        self.client = Groq(api_key=self.api_key)
        self.model = model or os.getenv("GROQ_MODEL", GROQ_MODEL)
        self.temperature = GROQ_TEMPERATURE
        self.max_tokens = GROQ_MAX_TOKENS

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send a chat completion request with retry logic.

        Args:
            system_prompt: System message setting the LLM's behavior.
            user_prompt: User message with the actual request.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.

        Returns:
            The LLM's text response.

        Raises:
            RuntimeError: If all retry attempts fail.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"LLM request attempt {attempt}/{MAX_RETRIES}")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature or self.temperature,
                    max_tokens=max_tokens or self.max_tokens,
                )
                content = response.choices[0].message.content
                logger.info(f"LLM response received ({len(content)} chars)")
                return content

            except RateLimitError as e:
                last_error = e
                delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
                logger.warning(
                    f"Rate limited (attempt {attempt}/{MAX_RETRIES}). "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)

            except APIConnectionError as e:
                last_error = e
                delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
                logger.warning(
                    f"Connection error (attempt {attempt}/{MAX_RETRIES}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)

            except APIError as e:
                last_error = e
                # Don't retry on client errors (4xx except 429 which is RateLimitError)
                if hasattr(e, "status_code") and 400 <= e.status_code < 500:
                    logger.error(f"Client error (not retrying): {e}")
                    raise RuntimeError(f"LLM API client error: {e}") from e
                delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
                logger.warning(
                    f"API error (attempt {attempt}/{MAX_RETRIES}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)

        raise RuntimeError(
            f"LLM request failed after {MAX_RETRIES} attempts. Last error: {last_error}"
        )

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """
        Send a chat request and parse the response as JSON.
        Handles responses that may have markdown code fences around JSON.

        Returns:
            Parsed JSON as a dictionary.

        Raises:
            ValueError: If the response cannot be parsed as JSON.
        """
        # Instruct the LLM to return pure JSON
        json_system = (
            system_prompt
            + "\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "Do not include any text before or after the JSON object. "
            "Do not wrap it in markdown code fences."
        )

        raw = self.chat(json_system, user_prompt, temperature, max_tokens)

        # Try to extract JSON from the response
        return self._parse_json_response(raw)

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """
        Parse JSON from LLM response, handling common formatting issues.
        """
        cleaned = text.strip()

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code fences
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try to find a JSON object in the text
        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"Failed to parse JSON from LLM response. Raw response:\n{text[:500]}"
        )
