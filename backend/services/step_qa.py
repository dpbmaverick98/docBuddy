"""
Step Q&A service
Answers questions about specific steps using context from summaries
"""
from anthropic import Anthropic
import os
from dotenv import load_dotenv

load_dotenv()


class StepQAService:
    def __init__(self, temperature: float = 0.7):
        """
        Initialize Q&A service
        
        Args:
            temperature: Temperature for Q&A (higher = more conversational)
        """
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.claude = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5"
        self.temperature = temperature
    
    def answer_question(
        self,
        step_title: str,
        step_description: str,
        context: str,
        question: str
    ) -> str:
        """
        Answer a question about a step using context
        
        Args:
            step_title: Title of the step
            step_description: Description of the step
            context: Summary context from documentation
            question: User's question
        
        Returns:
            Answer to the question
        """
        prompt = f"""You are a helpful developer assistant helping someone implement a step in their documentation journey.

Step: {step_title}
Description: {step_description}

Relevant Documentation Context:
{context}

User Question: {question}

Provide a clear, actionable answer focused on what the developer needs to do. Include:
- Specific steps or code examples if relevant
- Configuration details
- API calls or functions to use
- Any important gotchas or tips

Keep the answer concise but complete. If you don't have enough information from the context, say so and suggest checking the full documentation."""

        try:
            response = self.claude.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=self.temperature,  # Use configured temperature
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract text from response
            answer = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    answer += block.text
                elif isinstance(block, str):
                    answer += block
            
            return answer.strip()
            
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}. Please try rephrasing your question."

