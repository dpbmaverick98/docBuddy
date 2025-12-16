"""
Token optimization and semantic content selection
Intelligently manages token usage through content compression and relevance scoring
"""
import re
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from collections import Counter

# Download NLTK data if needed
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

@dataclass
class TokenBudget:
    """Token budget configuration"""
    max_tokens: int
    reserve_for_response: int = 500  # Reserve tokens for LLM response
    min_per_section: int = 50        # Minimum tokens per relevant section
    
    @property
    def available_tokens(self) -> int:
        """Tokens available for context"""
        return self.max_tokens - self.reserve_for_response

class ContentOptimizer:
    """
    Optimizes content for minimal token usage while maximizing relevance
    """
    
    def __init__(self):
        # Common stop words that add little semantic value
        self.stop_words = set([
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        ])
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using a simple heuristic
        More accurate than character-based estimation
        """
        if not text:
            return 0
        
        # Tokenize into words
        words = word_tokenize(text)
        
        # Count words, punctuation, and special tokens
        token_count = len(words)
        
        # Adjust for typical token-to-word ratios (usually ~1.3-1.5 for English)
        estimated_tokens = int(token_count * 1.3)
        
        return estimated_tokens
    
    def extract_relevant_sentences(
        self, 
        content: str, 
        query: str, 
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Extract most relevant sentences from content based on query keywords
        
        Args:
            content: Source content
            query: User query to match against
            max_tokens: Maximum tokens to include
            
        Returns:
            Optimized content string
        """
        if not content or not content.strip():
            return ""
        
        # Extract query keywords
        query_words = set(word.lower() for word in word_tokenize(query.lower()) 
                         if word.isalpha() and len(word) > 2)
        
        # Split into sentences
        sentences = sent_tokenize(content)
        
        if not sentences:
            return content[:200] + "..." if len(content) > 200 else content
        
        # Score each sentence by relevance
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            score = self._score_sentence_relevance(sentence, query_words)
            scored_sentences.append((score, i, sentence))
        
        # Sort by relevance score (descending)
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        
        # Select sentences within token budget
        selected_sentences = []
        current_tokens = 0
        
        for score, idx, sentence in scored_sentences:
            sentence_tokens = self.estimate_tokens(sentence)
            
            # Skip if no relevance or exceeds budget
            if score == 0:
                continue
                
            if max_tokens and current_tokens + sentence_tokens > max_tokens:
                # Try to fit a truncated version
                remaining_tokens = max_tokens - current_tokens
                if remaining_tokens > self.estimate_tokens(sentence[:100]):
                    # Fit partial sentence
                    truncated = self._smart_truncate(sentence, remaining_tokens)
                    selected_sentences.append(f"[...] {truncated}")
                break
            
            selected_sentences.append(sentence)
            current_tokens += sentence_tokens
            
            # Stop if we have enough high-relevance content
            if len(selected_sentences) >= 3 and current_tokens > max_tokens * 0.8:
                break
        
        # Reconstruct content maintaining original order
        if selected_sentences:
            # Sort by original index to maintain flow
            selected_with_indices = [(s, idx) for score, idx, s in scored_sentences 
                                   if s in selected_sentences]
            selected_with_indices.sort(key=lambda x: x[1])
            
            optimized_content = " ".join([s for s, idx in selected_with_indices])
            return optimized_content
        else:
            # Fallback: return first part of content
            return content[:200] + "..." if len(content) > 200 else content
    
    def _score_sentence_relevance(self, sentence: str, query_words: set) -> float:
        """Score sentence relevance based on query keywords"""
        sentence_words = set(word.lower() for word in word_tokenize(sentence.lower()) 
                           if word.isalpha())
        
        # Exact keyword matches
        exact_matches = len(query_words.intersection(sentence_words))
        
        # Partial matches (word contains query word)
        partial_matches = 0
        for q_word in query_words:
            for s_word in sentence_words:
                if q_word in s_word or s_word in q_word:
                    partial_matches += 1
                    break
        
        # Calculate relevance score
        score = (exact_matches * 2 + partial_matches * 1)
        
        # Boost score for sentences with technical keywords
        tech_keywords = {'api', 'function', 'method', 'class', 'component', 
                        'config', 'setup', 'install', 'authentication', 'token',
                        'endpoint', 'request', 'response', 'parameter', 'return'}
        tech_matches = len(tech_keywords.intersection(sentence_words))
        score += tech_matches * 1.5
        
        # Penalty for very short or very long sentences
        sentence_length = len(sentence.split())
        if sentence_length < 3:
            score *= 0.5
        elif sentence_length > 50:
            score *= 0.8
        
        return score
    
    def _smart_truncate(self, text: str, max_tokens: int) -> str:
        """Truncate text intelligently to fit token budget"""
        if not text:
            return ""
        
        # Estimate how many characters we can use
        avg_chars_per_token = 4  # Rough estimate
        max_chars = max_tokens * avg_chars_per_token
        
        if len(text) <= max_chars:
            return text
        
        # Try to truncate at sentence boundary
        sentences = sent_tokenize(text)
        truncated = ""
        
        for sentence in sentences:
            if len(truncated + sentence) <= max_chars:
                truncated += sentence + " "
            else:
                break
        
        if not truncated:
            # Fallback: character-level truncation
            truncated = text[:max_chars].rstrip()
        
        return truncated.rstrip() + "..."
    
    def optimize_context_window(
        self, 
        documents: List[Dict], 
        query: str, 
        budget: TokenBudget
    ) -> List[Dict]:
        """
        Optimize context window by selecting most relevant documents and content
        
        Args:
            documents: List of document dicts with content, metadata, score
            query: User query
            budget: Token budget configuration
            
        Returns:
            Optimized list of documents
        """
        if not documents:
            return []
        
        # Sort by relevance score
        sorted_docs = sorted(documents, key=lambda x: x.get('score', 0), reverse=True)
        
        optimized_docs = []
        current_tokens = 0
        
        for doc in sorted_docs:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            # Skip if no content
            if not content:
                continue
            
            # Optimize content for relevance
            remaining_budget = budget.available_tokens - current_tokens
            if remaining_budget <= budget.min_per_section:
                break
            
            optimized_content = self.extract_relevant_sentences(
                content, query, remaining_budget
            )
            
            content_tokens = self.estimate_tokens(optimized_content)
            
            # Include document if it provides meaningful content
            if content_tokens >= budget.min_per_section and content_tokens <= remaining_budget:
                optimized_doc = doc.copy()
                optimized_doc['content'] = optimized_content
                optimized_doc['optimized_tokens'] = content_tokens
                optimized_docs.append(optimized_doc)
                current_tokens += content_tokens
        
        return optimized_docs
    
    def calculate_optimal_token_budget(
        self, 
        query_complexity: str = 'intermediate',
        max_response_tokens: int = 3000
    ) -> TokenBudget:
        """
        Calculate optimal token budget based on query complexity and model limits
        
        Args:
            query_complexity: 'beginner', 'intermediate', or 'advanced'
            max_response_tokens: Maximum tokens for model response
            
        Returns:
            Optimized token budget
        """
        # Base context sizes by complexity
        base_context = {
            'beginner': 2000,    # Simpler queries need less context
            'intermediate': 3000, # Balanced approach
            'advanced': 4000     # Complex queries need more context
        }.get(query_complexity, 3000)
        
        # Calculate total budget with reserve for response
        total_budget = base_context + max_response_tokens
        
        return TokenBudget(
            max_tokens=total_budget,
            reserve_for_response=max_response_tokens,
            min_per_section=50
        )


def optimize_documents_for_context(
    documents: List[Dict], 
    query: str, 
    query_complexity: str = 'intermediate',
    max_response_tokens: int = 3000
) -> List[Dict]:
    """
    Convenience function to optimize documents for context window
    
    Args:
        documents: List of document dicts
        query: User query
        query_complexity: Complexity level
        max_response_tokens: Max tokens for response
        
    Returns:
        Optimized document list
    """
    optimizer = ContentOptimizer()
    budget = optimizer.calculate_optimal_token_budget(
        query_complexity, max_response_tokens
    )
    
    return optimizer.optimize_context_window(documents, query, budget)