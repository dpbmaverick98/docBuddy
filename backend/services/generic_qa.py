"""
Generic Q&A service
Answers single questions using RAG pipeline with optional context
Uses K2 as default model and returns answers similar to step Q&A format
"""
from services.llm_service import get_llm_service
from services.rag_engine import RAGEngine
from services.intent_extractor import IntentExtractor
from services.semantic_truncation import truncate_context as semantic_truncate_fn
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


class GenericQAService:
    def __init__(self, temperature: float = 0.7, model_name: str = "hf-k2-openai"):
        """
        Initialize generic Q&A service

        Args:
            temperature: Temperature for Q&A (higher = more conversational)
            model_name: LLM model to use (default: "hf-k2-openai" for K2)
        """
        self.model_name = model_name
        self.temperature = temperature

        # Initialize components
        self.llm = get_llm_service(model_name)
        self.intent_extractor = IntentExtractor(model_name=model_name)

    def answer_question(
        self,
        question: str,
        project: str = "polymarket",
        context: Optional[str] = None
    ) -> Dict:
        """
        Answer a single question using RAG pipeline with optional context

        Args:
            question: User's question
            project: Project name for collection lookup (default: "polymarket")
            context: Optional additional context (previous chat, journey, code, etc.)

        Returns:
            Dict with answer, sources, and confidence score
        """
        try:
            # Convert project name to collection name
            collection_name = project.lower().replace(' ', '_')

            # Initialize RAG engine for this collection
            rag_engine = RAGEngine(collection_name=collection_name)

            # Extract intent from question (and context if provided)
            query_for_intent = question
            if context:
                # Combine question and context for better intent extraction
                query_for_intent = f"{question}\n\nContext: {context}"

            intent = self.intent_extractor.extract_intent(query_for_intent)

            # Use RAG to retrieve relevant documents
            # Pass intent for better query expansion and filtering
            relevant_docs = rag_engine.query_with_intent(
                query=question,
                intent=intent,
                top_k=10,  # Get more results for better context
                use_cohere_optimizations=True
            )

            # Optimize context using semantic truncation
            if relevant_docs:
                try:
                    optimized_docs = semantic_truncate_fn(
                        docs=relevant_docs,
                        max_tokens=4000,  # Leave room for question and prompt
                        model_name=self.model_name
                    )
                except Exception as e:
                    print(f"⚠️ Semantic truncation failed: {e}, using top results")
                    optimized_docs = relevant_docs[:5]  # Fallback to top 5
            else:
                optimized_docs = []

            # Build context from retrieved documents
            context_parts = []
            for doc in optimized_docs:
                content = doc.get('content', '').strip()
                if content:
                    doc_title = doc.get('doc_title', doc.get('heading', ''))
                    if doc_title:
                        context_parts.append(f"From {doc_title}:\n{content}")
                    else:
                        context_parts.append(content)

            retrieved_context = "\n\n".join(context_parts)

            # Include user-provided context if available
            if context:
                if retrieved_context:
                    full_context = f"User-provided context:\n{context}\n\nRetrieved documentation:\n{retrieved_context}"
                else:
                    full_context = f"User-provided context:\n{context}"
            else:
                full_context = retrieved_context

            # Generate answer using LLM
            answer = self._generate_answer(question, full_context)

            # Calculate confidence score based on retrieval results
            confidence_score = self._calculate_confidence_score(relevant_docs, intent)

            # Format sources for response
            sources = self._format_sources(optimized_docs)

            return {
                "answer": answer,
                "sources": sources,
                "confidence_score": confidence_score
            }

        except Exception as e:
            print(f"⚠️ Generic Q&A error: {e}")
            # Return a basic answer without RAG if everything fails
            try:
                basic_answer = self._generate_basic_answer(question, context)
                return {
                    "answer": basic_answer,
                    "sources": [],
                    "confidence_score": 0.0
                }
            except Exception as basic_error:
                return {
                    "answer": f"Sorry, I encountered an error answering your question: {str(e)}. Please try rephrasing your question.",
                    "sources": [],
                    "confidence_score": 0.0
                }

    def _generate_answer(self, question: str, context: str) -> str:
        """
        Generate answer using LLM with retrieved context

        Args:
            question: User's question
            context: Retrieved and user context combined

        Returns:
            Formatted answer string
        """
        if not context.strip():
            # No context available, provide general guidance
            prompt = f"""You are a helpful developer assistant.

User Question: {question}

Please provide a helpful answer based on general knowledge. If you don't have specific information about this topic, suggest where they might find more information.

Keep the answer concise but complete."""
        else:
            # Use retrieved context
            prompt = f"""You are a helpful developer assistant answering questions about documentation.

Retrieved Documentation Context:
{context}

User Question: {question}

Provide a clear, actionable answer focused on what the developer needs to do. Include:
- Specific steps or code examples if relevant
- Configuration details
- API calls or functions to use
- Any important gotchas or tips

Keep the answer concise but complete. If you don't have enough information from the context, say so and suggest checking the full documentation.

Format your answer in markdown for clarity."""

        try:
            response = self.llm.generate(
                prompt=prompt,
                max_tokens=2000,  # Allow longer answers for comprehensive responses
                temperature=self.temperature
            )

            return response.strip()

        except Exception as e:
            print(f"⚠️ LLM generation failed: {e}")
            return f"Sorry, I encountered an error generating the answer: {str(e)}. Please try again."

    def _generate_basic_answer(self, question: str, context: Optional[str] = None) -> str:
        """
        Generate a basic answer without RAG when everything else fails

        Args:
            question: User's question
            context: Optional user context

        Returns:
            Basic answer string
        """
        prompt = f"""You are a helpful developer assistant.

User Question: {question}"""

        if context:
            prompt += f"\n\nContext: {context}"

        prompt += "\n\nProvide a helpful answer based on general knowledge."

        try:
            response = self.llm.generate(
                prompt=prompt,
                max_tokens=1000,
                temperature=self.temperature
            )
            return response.strip()
        except Exception as e:
            return "I'm sorry, I encountered an error. Please try again or rephrase your question."

    def _calculate_confidence_score(self, docs: List[Dict], intent: Dict) -> float:
        """
        Calculate confidence score based on retrieval results and intent matching

        Args:
            docs: Retrieved documents
            intent: Extracted intent

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not docs:
            return 0.0

        # Base confidence on average relevance score
        total_score = sum(doc.get('relevance_score', doc.get('score', 0.5)) for doc in docs)
        avg_score = total_score / len(docs)

        # Boost confidence if we have good intent extraction
        intent_boost = 0.1 if intent and intent.get('keywords') else 0.0

        # Cap at 0.9 to leave room for uncertainty
        confidence = min(avg_score + intent_boost, 0.9)

        return round(confidence, 2)

    def _format_sources(self, docs: List[Dict]) -> List[Dict]:
        """
        Format retrieved documents for API response

        Args:
            docs: Retrieved document chunks

        Returns:
            List of formatted source objects
        """
        sources = []
        for doc in docs:
            source = {
                "doc_path": doc.get('doc_path', ''),
                "doc_url": doc.get('doc_url', ''),
                "doc_title": doc.get('doc_title', ''),
                "heading": doc.get('heading', ''),
                "content": doc.get('content', ''),
                "score": doc.get('relevance_score', doc.get('score', 0.5))
            }
            sources.append(source)

        return sources