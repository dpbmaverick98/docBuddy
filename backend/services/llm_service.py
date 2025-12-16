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


class HuggingFaceOpenAICompatibleService(BaseLLMService):
    """HuggingFace models via OpenAI-compatible API"""

    def __init__(self, model_id: str = "moonshotai/Kimi-K2-Instruct:novita"):
        """
        Initialize HuggingFace service with specified model
        
        Args:
            model_id: HuggingFace model ID (can use :provider suffix for routing)
        """
        self.api_key = os.getenv('HF_TOKEN')
        self.client = None
        self.model = model_id
        print(f"✅ HuggingFace service initialized with {model_id} (will check token on first use)")

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate text using HuggingFace models via OpenAI-compatible API"""
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
            print(f"⚠️  HuggingFace error with {self.model}: {e}")
            raise


# Backward compatibility alias
class HuggingFaceK2OpenAIService(HuggingFaceOpenAICompatibleService):
    """Legacy K2-Instruct service (use HuggingFaceOpenAICompatibleService instead)"""
    def __init__(self):
        super().__init__(model_id="moonshotai/Kimi-K2-Instruct:novita")


def get_llm_service(model_name: str = "claude") -> BaseLLMService:
    """
    Factory function to get LLM service based on model name

    Args:
        model_name: One of:
            - "claude": Claude Sonnet 4.5
            - "hf-k2-openai" or "k2": Kimi K2-Instruct
            - "hf-mistral": Mistral (fast, cheaper)
            - "hf-llama": Meta Llama 3.1 (70B)
            - "hf-qwen": Qwen 2.5 (72B)
            - "hf-mixtral": Mixtral 8x7B (fast MoE)
            - Custom HuggingFace model ID starting with "hf-"

    Returns:
        LLM service instance
    """
    model_name = model_name.lower().strip()

    # Map common aliases to HuggingFace model IDs
    hf_model_mapping = {
        "hf-k2-openai": "moonshotai/Kimi-K2-Instruct:novita",
        "k2": "moonshotai/Kimi-K2-Instruct:novita",
        "hf-mistral": "mistralai/Mistral-7B-Instruct-v0.2:vllm",
        "hf-llama": "meta-llama/Llama-3.1-70B-Instruct:vllm",
        "hf-qwen": "Qwen/Qwen2.5-72B-Instruct:vllm",
        "hf-mixtral": "mistralai/Mixtral-8x7B-Instruct-v0.1:vllm",
        "mistral": "mistralai/Mistral-7B-Instruct-v0.2:vllm",
        "llama": "meta-llama/Llama-3.1-70B-Instruct:vllm",
        "qwen": "Qwen/Qwen2.5-72B-Instruct:vllm",
        "mixtral": "mistralai/Mixtral-8x7B-Instruct-v0.1:vllm",
    }

    if model_name == "claude":
        return ClaudeService()
    elif model_name in hf_model_mapping:
        # Return HuggingFace service with mapped model
        return HuggingFaceOpenAICompatibleService(hf_model_mapping[model_name])
    elif model_name.startswith("hf-"):
        # Custom HuggingFace model ID
        custom_model_id = model_name[3:]  # Remove "hf-" prefix
        return HuggingFaceOpenAICompatibleService(custom_model_id)
    else:
        print(f"⚠️  Unknown model '{model_name}', defaulting to Claude")
        return ClaudeService()
