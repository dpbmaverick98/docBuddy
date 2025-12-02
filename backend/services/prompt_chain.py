"""
Prompt chaining system
Manages multi-step prompt workflows with context optimization
"""
from typing import Dict, List, Optional, Any
from anthropic import Anthropic
import os
from dotenv import load_dotenv

load_dotenv()


class PromptChain:
    def __init__(self, temperature: float = 0.7, max_tokens: int = 4000):
        """
        Initialize prompt chain
        
        Args:
            temperature: Default temperature for generation (0.0-1.0)
            max_tokens: Maximum tokens per response
        """
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.claude = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5"
        self.default_temperature = temperature
        self.default_max_tokens = max_tokens
    
    def execute_chain(
        self,
        steps: List[Dict[str, Any]],
        initial_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a chain of prompts with context passing
        
        Args:
            steps: List of step configs, each with:
                - name: Step identifier
                - prompt: Prompt template
                - temperature: Optional override
                - max_tokens: Optional override
                - extract: Function to extract data from response
            initial_context: Initial context dict
        
        Returns:
            Dict with results from each step
        """
        context = initial_context or {}
        results = {}
        
        for step in steps:
            step_name = step['name']
            prompt_template = step['prompt']
            temperature = step.get('temperature', self.default_temperature)
            max_tokens = step.get('max_tokens', self.default_max_tokens)
            
            # Format prompt with context
            prompt = self._format_prompt(prompt_template, context)
            
            # Execute step
            response = self._execute_step(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract data if extractor provided
            if 'extract' in step:
                extracted = step['extract'](response, context)
                context[step_name] = extracted
                results[step_name] = extracted
            else:
                context[step_name] = response
                results[step_name] = response
        
        return results
    
    def _format_prompt(self, template: str, context: Dict) -> str:
        """
        Format prompt template with context
        
        Args:
            template: Prompt template with {variable} placeholders
            context: Context dict with variables
        
        Returns:
            Formatted prompt
        """
        try:
            return template.format(**context)
        except KeyError as e:
            # If variable missing, use empty string
            return template.format(**{k: context.get(k, '') for k in context})
    
    def _execute_step(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """
        Execute a single prompt step
        
        Args:
            prompt: Prompt text
            temperature: Temperature for this step
            max_tokens: Max tokens
        
        Returns:
            Response text
        """
        try:
            response = self.claude.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract text
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text
                elif isinstance(block, str):
                    response_text += block
            
            return response_text.strip()
            
        except Exception as e:
            return f"Error in prompt execution: {str(e)}"
    
    def optimize_context(
        self,
        docs: List[Dict],
        max_tokens: int = 3000
    ) -> List[Dict]:
        """
        Optimize context by selecting most relevant docs
        
        Args:
            docs: List of doc dicts with content, metadata, score
            max_tokens: Maximum tokens for context
        
        Returns:
            Optimized list of docs
        """
        # Sort by score (highest first)
        sorted_docs = sorted(
            docs,
            key=lambda x: x.get('score', 0) or x.get('distance', 1),
            reverse=True
        )
        
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        selected = []
        current_tokens = 0
        
        for doc in sorted_docs:
            content = doc.get('content', '')
            doc_tokens = len(content) // 4
            
            if current_tokens + doc_tokens <= max_tokens:
                selected.append(doc)
                current_tokens += doc_tokens
            else:
                # Try to fit partial content
                remaining_tokens = max_tokens - current_tokens
                if remaining_tokens > 100:  # Only if meaningful space left
                    partial_content = content[:remaining_tokens * 4]
                    doc_copy = doc.copy()
                    doc_copy['content'] = partial_content + "..."
                    selected.append(doc_copy)
                break
        
        return selected

