"""
Step Q&A service
Answers questions about specific steps using context from summaries
Uses Claude Sonnet 4.5
"""
from services.llm_service import get_llm_service
from dotenv import load_dotenv

load_dotenv()


class StepQAService:
    def __init__(self, temperature: float = 0.7, model_name: str = "claude", x402_client=None):
        """
        Initialize Q&A service

        Args:
            temperature: Temperature for Q&A (higher = more conversational)
            model_name: LLM model to use ("claude", "hf-k2-openai")
            x402_client: x402 client for payment-enabled requests
        """
        self.temperature = temperature
        self.model_name = model_name
        self.x402_client = x402_client

        if model_name != "hf-k2-openai":
            # Use direct LLM service
            self.llm = get_llm_service(model_name)
        else:
            # Will use x402 client
            self.llm = None
    
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
            # Use LLM for Q&A
            if self.model_name == "hf-k2-openai" and self.x402_client:
                # Try x402 K2 service first, fallback to direct LLM if it fails
                try:
                    answer = self.x402_client.k2_generate(
                        prompt=prompt,
                        max_tokens=1000,
                        temperature=self.temperature
                    )
                    # 💰 x402 Payment
                    if not answer:
                        print("⚠️ x402 returned empty, falling back to direct LLM")
                        answer = None
                except Exception as x402_error:
                    # Fallback to direct LLM if x402 fails
                    error_msg = str(x402_error).lower()
                    if "connection" in error_msg or "refused" in error_msg or "network" in error_msg:
                        print(f"⚠️ x402 service unavailable ({x402_error}), falling back to direct LLM...")
                    else:
                        print(f"⚠️ x402 error: {x402_error}, falling back to direct LLM...")
                    answer = None
                
                # Fallback to direct LLM if x402 failed
                if not answer:
                    if not self.llm:
                        raise Exception("No LLM service available as fallback")
                    answer = self.llm.generate(
                        prompt=prompt,
                        max_tokens=1000,
                        temperature=self.temperature
                    )
            else:
                # Use direct LLM service
                if not self.llm:
                    raise Exception("LLM service not initialized")
                answer = self.llm.generate(
                    prompt=prompt,
                    max_tokens=1000,
                    temperature=self.temperature
                )
            
            if not answer:
                raise Exception("No response from LLM service")
            
            return answer.strip()
            
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}. Please try rephrasing your question."

