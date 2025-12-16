"""
Prompt chaining system
Manages multi-step prompt workflows with context optimization
Uses semantic truncation for better context preservation
"""
from typing import Dict, List, Optional, Any
from services.llm_service import get_llm_service
from dotenv import load_dotenv

load_dotenv()


class PromptChain:
    def __init__(self, temperature: float = 0.7, max_tokens: int = 4000, model_name: str = "claude"):
        """
        Initialize prompt chain

        Args:
            temperature: Default temperature for generation (0.0-1.0)
            max_tokens: Maximum tokens per response
            model_name: LLM model to use ("claude", "hf-k2-openai")
        """
        self.default_temperature = temperature
        self.default_max_tokens = max_tokens
        self.model_name = model_name

        # Use selected model for prompt chaining
        self.llm = get_llm_service(model_name)
    
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
            # Use Claude for prompt execution
            response_text = self.llm.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response_text.strip()
            
        except Exception as e:
            return f"Error in prompt execution: {str(e)}"
    
    def optimize_context(
        self,
        docs: List[Dict],
        max_tokens: int = 3000
    ) -> List[Dict]:
        """
        Optimize context using semantic truncation
        Intelligently preserves sentence/section boundaries and code blocks
        
        Args:
            docs: List of doc dicts with content, metadata, score
            max_tokens: Maximum tokens for context
        
        Returns:
            Optimized list of docs with semantically truncated content
        """
        # Sort by score (highest first)
        sorted_docs = sorted(
            docs,
            key=lambda x: x.get('score', 0) or x.get('distance', 1),
            reverse=True
        )
        
        # Try to use semantic truncation dynamically
        try:
            from services.semantic_truncation import truncate_context as semantic_truncate_fn
            return semantic_truncate_fn(sorted_docs, max_tokens, self.model_name)
        except Exception as e:
            print(f"⚠️ Semantic truncation failed: {e}, falling back to character-based")
        
        # Fallback to character-based truncation
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

