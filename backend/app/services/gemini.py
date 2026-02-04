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

    # Token tracking for logging
    last_prompt_tokens: int = 0
    last_completion_tokens: int = 0

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

            # Track token usage if available
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    self.last_prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                    self.last_completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
                else:
                    # Estimate tokens (~4 chars per token)
                    self.last_prompt_tokens = len(full_prompt) // 4
                    self.last_completion_tokens = len(response.text) // 4 if response.text else 0
            except Exception:
                self.last_prompt_tokens = len(full_prompt) // 4
                self.last_completion_tokens = 0

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

        import re

        def extract_and_parse(text: str) -> dict[str, Any]:
            """Extract JSON from text and ensure it's a dict."""
            # Try direct parse first
            try:
                result = json.loads(text)
                if isinstance(result, dict):
                    return result
                elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                    logger.warning("Got list instead of dict, using first element")
                    return result[0]
            except json.JSONDecodeError as e:
                logger.info(f"Direct parse failed: {e}, trying regex extraction")

            # Try to find JSON object - find first { and last }
            first_brace = text.find('{')
            last_brace = text.rfind('}')

            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                json_text = text[first_brace:last_brace + 1]
                try:
                    result = json.loads(json_text)
                    if isinstance(result, dict):
                        return result
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse failed: {e}, attempting to repair truncated JSON")

                    # Try to repair truncated JSON by closing open structures
                    repaired = repair_truncated_json(json_text)
                    if repaired:
                        try:
                            result = json.loads(repaired)
                            if isinstance(result, dict):
                                logger.info("Successfully repaired truncated JSON")
                                return result
                        except json.JSONDecodeError:
                            pass

                    logger.error(f"Could not repair JSON. Length: {len(json_text)}, first 200 chars: {json_text[:200]}")

            raise json.JSONDecodeError("No valid JSON object found", text[:200], 0)

        def repair_truncated_json(text: str) -> str | None:
            """Attempt to repair a truncated JSON by closing open structures."""
            # Count open brackets and braces
            open_braces = 0
            open_brackets = 0
            in_string = False
            escape_next = False

            for char in text:
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == '{':
                    open_braces += 1
                elif char == '}':
                    open_braces -= 1
                elif char == '[':
                    open_brackets += 1
                elif char == ']':
                    open_brackets -= 1

            # If we have unclosed structures, try to close them
            if open_braces > 0 or open_brackets > 0:
                # Remove any trailing incomplete value
                text = text.rstrip()
                # Remove trailing comma if present
                if text.endswith(','):
                    text = text[:-1]
                # Remove incomplete string
                if in_string:
                    # Find last complete string
                    last_quote = text.rfind('"')
                    if last_quote > 0:
                        text = text[:last_quote + 1]

                # Close open structures
                text += ']' * open_brackets
                text += '}' * open_braces
                return text

            return None

        try:
            # First, try to extract JSON from markdown code block
            # Match ```json or ``` followed by content until closing ```
            code_block_match = re.search(r'```(?:json)?[\s\n]*([\s\S]+?)[\s\n]*```', text_response)
            if code_block_match:
                cleaned = code_block_match.group(1).strip()
                logger.debug(f"Extracted from code block: {cleaned[:100]}...")
                return extract_and_parse(cleaned)

            # No code block, try direct parse
            cleaned = text_response.strip()
            return extract_and_parse(cleaned)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.debug(f"Raw response: {text_response[:1000]}")
            raise ValueError(f"Could not parse JSON from response: {text_response[:200]}...")
