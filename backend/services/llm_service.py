"""
LLM service - Claude Sonnet 4.5
Simple, reliable LLM service using Claude
"""
from anthropic import Anthropic
import os
from dotenv import load_dotenv

load_dotenv()


class ClaudeService:
    """Claude Sonnet 4.5 - reliable and consistent"""
    
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5"
        print(f"✅ Using Claude Sonnet 4.5")
    
    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate text using Claude Sonnet 4.5
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation (0.0-1.0)
        
        Returns:
            Generated text
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract text from response
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
