"""
LLM service - Multi-model support
Supports Claude, Gemini, and HuggingFace models
"""
from anthropic import Anthropic
from openai import OpenAI
import os
from dotenv import load_dotenv
from abc import ABC, abstractmethod

# Try to load dotenv, but don't fail if .env file is not accessible
try:
    load_dotenv()
except Exception:
    # Silently continue if .env loading fails (e.g., permission issues)
    pass


class BaseLLMService(ABC):
    """Base class for LLM services"""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate text from prompt"""
        pass


class ClaudeService(BaseLLMService):
    """Claude Sonnet 4.5 - reliable and consistent"""

    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.client = None
        self.model = "claude-sonnet-4-5"
        print(f"✅ Claude service initialized (will check token on first use)")

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate text using Claude Sonnet 4.5"""
        try:
            # Lazy initialization - check token and create client only when needed
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")

            if not self.client:
                self.client = Anthropic(api_key=self.api_key)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text
                elif isinstance(block, str):
                    response_text += block

            return response_text.strip()

        except Exception as e:
            print(f"⚠️  Claude error: {e}")
            raise


class HuggingFaceK2OpenAIService(BaseLLMService):
    """HuggingFace K2-Instruct model via OpenAI-compatible API"""

    def __init__(self):
        self.api_key = os.getenv('HF_TOKEN')
        self.client = None
        self.model = "moonshotai/Kimi-K2-Instruct:novita"
        print(f"✅ HuggingFace K2-Instruct service initialized (will check token on first use)")

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate text using HuggingFace K2-Instruct via OpenAI client"""
        try:
            # Lazy initialization - check token and create client only when needed
            if not self.api_key:
                raise ValueError("HF_TOKEN environment variable not set")

            if not self.client:
                self.client = OpenAI(
                    base_url="https://router.huggingface.co/v1",
                    api_key=self.api_key,
                )

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )

            if completion.choices and len(completion.choices) > 0:
                message = completion.choices[0].message
                if hasattr(message, 'content'):
                    return message.content.strip()
                elif isinstance(message, str):
                    return message.strip()

            return ""

        except Exception as e:
            print(f"⚠️  HuggingFace K2 (OpenAI) error: {e}")
            raise


def get_llm_service(model_name: str = "claude") -> BaseLLMService:
    """
    Factory function to get LLM service based on model name

    Args:
        model_name: One of "claude", "hf-k2-openai"

    Returns:
        LLM service instance
    """
    model_name = model_name.lower()

    if model_name == "claude":
        return ClaudeService()
    elif model_name == "hf-k2-openai":
        # Return the service - it will check for token on first use
        return HuggingFaceK2OpenAIService()
    else:
        print(f"⚠️  Unknown model '{model_name}', defaulting to Claude")
        return ClaudeService()
