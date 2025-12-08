"""
Intent extraction service
Extracts user intent from queries for better context understanding
Uses Claude Sonnet 4.5
"""
import json
from typing import Dict, Optional
from dotenv import load_dotenv
from services.llm_service import get_llm_service

load_dotenv()


class IntentExtractor:
    def __init__(self, model_name: str = "claude"):
        """
        Initialize intent extractor

        Args:
            model_name: LLM model to use ("claude", "hf-k2-openai")
        """
        self.llm = get_llm_service(model_name)
    
    def extract_intent(self, user_query: str) -> Dict:
        """
        Extract structured intent from user query
        
        Returns:
            Dict with goal, complexity, platform, keywords, etc.
        """
        prompt = f"""Analyze this user query and extract structured intent:

User Query: "{user_query}"

For Privy documentation queries, pay special attention to:
- Dashboard/admin features
- Authentication flows  
- Wallet connections
- User management
- API integrations

Extract:
1. Main goal (what they want to accomplish)
2. Complexity level (beginner/intermediate/advanced) 
3. Platform/framework (privy, react, nextjs, etc.)
4. Key concepts/technologies mentioned
5. Specific requirements or constraints

Return ONLY valid JSON: {{
  "goal": "main objective",
  "complexity": "beginner|intermediate|advanced",
  "platform": "react|nextjs|python|etc or null",
  "keywords": ["keyword1", "keyword2"],
  "requirements": ["requirement1", "requirement2"],
  "context": "brief context about what they're trying to do"
}}"""

        try:
            # Use Claude for intent extraction
            response_text = self.llm.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3  # Lower temp for more deterministic extraction
            )
            
            response_text = response_text.strip()
            
            # Try to extract JSON if wrapped in markdown
            if "```json" in response_text:
                parts = response_text.split("```json")
                if len(parts) > 1:
                    json_part = parts[1].split("```")[0].strip()
                    if json_part:
                        response_text = json_part
            elif "```" in response_text:
                parts = response_text.split("```")
                if len(parts) > 1:
                    json_part = parts[1].split("```")[0].strip()
                    if json_part:
                        response_text = json_part
            
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

