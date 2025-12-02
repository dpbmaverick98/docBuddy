"""
Intent extraction service
Extracts user intent from queries for better context understanding
"""
from anthropic import Anthropic
import os
import json
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class IntentExtractor:
    def __init__(self):
        """Initialize intent extractor"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.claude = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5"
    
    def extract_intent(self, user_query: str) -> Dict:
        """
        Extract structured intent from user query
        
        Returns:
            Dict with goal, complexity, platform, keywords, etc.
        """
        prompt = f"""Analyze this user query and extract structured intent:

User Query: "{user_query}"

Extract:
1. Main goal (what they want to accomplish)
2. Complexity level (beginner/intermediate/advanced)
3. Platform/framework (if mentioned: react, nextjs, python, etc.)
4. Key concepts/technologies mentioned
5. Specific requirements or constraints

Return ONLY valid JSON:
{{
  "goal": "main objective",
  "complexity": "beginner|intermediate|advanced",
  "platform": "react|nextjs|python|etc or null",
  "keywords": ["keyword1", "keyword2"],
  "requirements": ["requirement1", "requirement2"],
  "context": "brief context about what they're trying to do"
}}"""

        try:
            response = self.claude.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,  # Lower temp for more deterministic extraction
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract JSON from response
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text
                elif isinstance(block, str):
                    response_text += block
            
            response_text = response_text.strip()
            
            # Try to extract JSON if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            intent = json.loads(response_text)
            return intent
            
        except Exception as e:
            # Fallback: return basic intent
            return {
                "goal": user_query,
                "complexity": "intermediate",
                "platform": None,
                "keywords": user_query.lower().split(),
                "requirements": [],
                "context": user_query
            }

