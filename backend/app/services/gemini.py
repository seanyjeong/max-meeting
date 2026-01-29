"""
Google Gemini LLM provider implementation.

Uses Gemini Flash model for cost-effective meeting processing.
Based on spec Section 9 (LLM Prompt Strategy).
"""

import asyncio
import json
import logging
from typing import Any

from app.services.llm import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini Flash LLM provider."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Gemini API key is required")

        self.api_key = api_key
        self._model = None
        self._configure()

    def _configure(self) -> None:
        """Configure the Gemini client."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self._genai = genai

            # Use Gemini Flash for cost efficiency
            self._model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                },
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE",
                    },
                ],
            )

            logger.info("Gemini provider configured successfully")

        except ImportError:
            logger.error("google-generativeai not installed")
            raise RuntimeError("google-generativeai is not installed")
        except Exception as e:
            logger.error(f"Failed to configure Gemini: {e}")
            raise

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate text using Gemini.

        Args:
            prompt: User prompt
            system_prompt: Optional system instruction
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text string
        """
        try:
            # Build the full prompt with system instruction
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Create a model instance with custom config
            model = self._genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                generation_config={
                    "temperature": temperature,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": max_tokens,
                },
            )

            # Generate response asynchronously to avoid blocking event loop
            response = await asyncio.to_thread(model.generate_content, full_prompt)

            if response.text:
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return ""

        except Exception as e:
            logger.error(f"Gemini text generation failed: {e}")
            raise

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """
        Generate JSON response using Gemini.

        Args:
            prompt: User prompt (should request JSON output)
            system_prompt: Optional system instruction
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (lower for more deterministic JSON)

        Returns:
            Parsed JSON dict
        """
        # Enhance prompt to ensure JSON output
        json_prompt = f"{prompt}\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanations."

        text_response = await self.generate_text(
            prompt=json_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        try:
            # Clean up potential markdown code blocks
            cleaned = text_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            return json.loads(cleaned)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.debug(f"Raw response: {text_response}")

            # Try to extract JSON from the response
            try:
                import re
                json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())

                # Try array format
                array_match = re.search(r'\[.*\]', text_response, re.DOTALL)
                if array_match:
                    return json.loads(array_match.group())

            except Exception:
                pass

            raise ValueError(f"Could not parse JSON from response: {text_response[:200]}...")
