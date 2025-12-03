"""
Step Q&A service
Answers questions about specific steps using context from summaries
Uses Claude Sonnet 4.5
"""
from services.llm_service import ClaudeService
from dotenv import load_dotenv

load_dotenv()


class StepQAService:
    def __init__(self, temperature: float = 0.7):
        """
        Initialize Q&A service with Claude
        
        Args:
            temperature: Temperature for Q&A (higher = more conversational)
        """
        # Use Claude for Q&A
        self.llm = ClaudeService()
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
            # Use Claude for Q&A
            answer = self.llm.generate(
                prompt=prompt,
                max_tokens=1000,
                temperature=self.temperature
            )
            
            return answer.strip()
            
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}. Please try rephrasing your question."

