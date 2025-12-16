"""
Semantic context truncation
Preserves complete sentences, sections, and code blocks when truncating content
Uses accurate token counting with tiktoken
"""
import re
from typing import List, Dict, Optional, Tuple
import tiktoken

# Model to encoding mapping for tiktoken
MODEL_ENCODINGS = {
    "claude-3-sonnet-20240229": "cl100k_base",
    "claude-3-opus": "cl100k_base",
    "claude-3-haiku": "cl100k_base",
    "gpt-4": "cl100k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "mistral": "cl100k_base",  # Approximate
    "llama": "cl100k_base",  # Approximate
}


class SemanticTruncator:
    """Intelligently truncate content while preserving semantic boundaries"""
    
    def __init__(self, model_name: str = "claude-3-sonnet-20240229"):
        """
        Initialize truncator with encoding for specified model
        
        Args:
            model_name: LLM model name for token counting
        """
        self.model_name = model_name
        encoding_name = MODEL_ENCODINGS.get(model_name, "cl100k_base")
        
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            print(f"⚠️ Failed to load tiktoken encoding {encoding_name}: {e}")
            print("   Falling back to approximate token counting")
            self.encoding = None
    
    def count_tokens(self, text: str) -> int:
        """Count actual tokens in text"""
        if self.encoding:
            return len(self.encoding.encode(text))
        # Fallback: rough estimation (1 token ≈ 4 chars)
        return len(text) // 4
    
    def truncate_intelligently(
        self,
        content: str,
        max_tokens: int,
        preserve_code_blocks: bool = True
    ) -> str:
        """
        Intelligently truncate content preserving semantic boundaries
        
        Args:
            content: Content to truncate
            max_tokens: Maximum tokens allowed
            preserve_code_blocks: If True, try to keep complete code blocks
            
        Returns:
            Truncated content that fits within max_tokens
        """
        current_tokens = self.count_tokens(content)
        
        if current_tokens <= max_tokens:
            return content
        
        # Try different truncation strategies in order of preference
        
        # Strategy 1: Truncate at section boundaries (### or ##)
        truncated = self._truncate_at_sections(content, max_tokens)
        if truncated and self.count_tokens(truncated) <= max_tokens:
            return truncated
        
        # Strategy 2: Truncate at paragraph boundaries
        truncated = self._truncate_at_paragraphs(content, max_tokens)
        if truncated and self.count_tokens(truncated) <= max_tokens:
            return truncated
        
        # Strategy 3: Truncate at sentence boundaries
        truncated = self._truncate_at_sentences(content, max_tokens)
        if truncated and self.count_tokens(truncated) <= max_tokens:
            return truncated
        
        # Strategy 4: Truncate at word boundaries
        truncated = self._truncate_at_words(content, max_tokens)
        if truncated:
            return truncated
        
        # Fallback: Hard truncation (should rarely reach here)
        return self._hard_truncate(content, max_tokens)
    
    def _truncate_at_sections(self, content: str, max_tokens: int) -> Optional[str]:
        """Truncate after complete sections (### Heading)"""
        # Split by section headers (# ## ###)
        sections = re.split(r'(^#{1,3}\s+.+$)', content, flags=re.MULTILINE)
        
        result = ""
        current_tokens = 0
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            
            # Calculate tokens for this section
            section_tokens = self.count_tokens(section)
            
            if current_tokens + section_tokens <= max_tokens:
                result += section
                current_tokens += section_tokens
            else:
                # Try to include partial section if there's space
                if current_tokens < max_tokens and (max_tokens - current_tokens) > 50:
                    remaining = max_tokens - current_tokens
                    partial = self._truncate_at_words(section, remaining)
                    if partial:
                        result += partial
                break
        
        return result.strip() if result.strip() else None
    
    def _truncate_at_paragraphs(self, content: str, max_tokens: int) -> Optional[str]:
        """Truncate after complete paragraphs (double newline)"""
        paragraphs = content.split('\n\n')
        
        result = []
        current_tokens = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            
            para_tokens = self.count_tokens(para)
            
            if current_tokens + para_tokens <= max_tokens:
                result.append(para)
                current_tokens += para_tokens
            else:
                # Try to fit partial paragraph
                if current_tokens < max_tokens and (max_tokens - current_tokens) > 50:
                    remaining = max_tokens - current_tokens
                    partial = self._truncate_at_sentences(para, remaining)
                    if partial:
                        result.append(partial)
                break
        
        return '\n\n'.join(result) if result else None
    
    def _truncate_at_sentences(self, content: str, max_tokens: int) -> Optional[str]:
        """Truncate after complete sentences"""
        # Split by sentence boundaries (. ! ? \n)
        # But preserve code blocks (lines starting with ` or 4+ spaces)
        sentences = self._split_sentences_smart(content)
        
        result = []
        current_tokens = 0
        
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            sent_tokens = self.count_tokens(sentence)
            
            if current_tokens + sent_tokens <= max_tokens:
                result.append(sentence)
                current_tokens += sent_tokens
            else:
                break
        
        return ''.join(result).strip() if result else None
    
    def _truncate_at_words(self, content: str, max_tokens: int) -> Optional[str]:
        """Truncate at word boundaries"""
        words = content.split()
        
        result = []
        current_tokens = 0
        
        for word in words:
            word_tokens = self.count_tokens(word)
            
            if current_tokens + word_tokens + 1 <= max_tokens:  # +1 for space
                result.append(word)
                current_tokens += word_tokens + 1
            else:
                break
        
        return ' '.join(result) if result else None
    
    def _hard_truncate(self, content: str, max_tokens: int) -> str:
        """Last resort: hard truncation with ellipsis"""
        # Estimate character count needed
        if self.encoding:
            # Use actual encoding to find cutoff point
            tokens = self.encoding.encode(content)
            truncated_tokens = tokens[:max_tokens]
            return self.encoding.decode(truncated_tokens).rstrip() + "..."
        else:
            # Fallback: character-based (1 token ≈ 4 chars)
            char_limit = max_tokens * 4
            return content[:char_limit].rstrip() + "..."
    
    def _split_sentences_smart(self, content: str) -> List[str]:
        """
        Split content into sentences while preserving code blocks and structure
        
        Returns list of sentence fragments including punctuation
        """
        # This is a simplified sentence splitter
        # A more robust one would use NLTK or spaCy
        
        sentences = []
        current = ""
        in_code_block = False
        
        for line in content.split('\n'):
            # Check if entering/exiting code block
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
            
            # If in code block, preserve entire lines
            if in_code_block:
                current += line + '\n'
                sentences.append(current)
                current = ""
                continue
            
            # For regular text, split on sentence boundaries
            # Match sentence endings: . ! ? followed by space or newline
            matches = re.finditer(r'[.!?]+\s+', line)
            last_end = 0
            
            for match in matches:
                sentence = line[last_end:match.end()]
                current += sentence
                sentences.append(current)
                current = ""
                last_end = match.end()
            
            # Add remaining part
            remaining = line[last_end:]
            if remaining:
                current += remaining + '\n'
        
        # Add any remaining content
        if current.strip():
            sentences.append(current)
        
        return sentences


def truncate_context(
    docs: List[Dict],
    max_tokens: int = 3000,
    model_name: str = "claude-3-sonnet-20240229"
) -> List[Dict]:
    """
    Semantic context truncation for list of documents
    
    Args:
        docs: List of doc dicts with 'content' field
        max_tokens: Maximum total tokens
        model_name: LLM model for token counting
        
    Returns:
        List of docs with semantically truncated content
    """
    truncator = SemanticTruncator(model_name)
    
    selected_docs = []
    current_tokens = 0
    
    for doc in docs:
        content = doc.get('content', '')
        doc_tokens = truncator.count_tokens(content)
        
        if current_tokens + doc_tokens <= max_tokens:
            # Entire doc fits
            selected_docs.append(doc)
            current_tokens += doc_tokens
        else:
            # Try to fit partial doc
            remaining_tokens = max_tokens - current_tokens
            
            if remaining_tokens > 100:  # Only if meaningful space left
                truncated_content = truncator.truncate_intelligently(
                    content,
                    remaining_tokens
                )
                
                if truncated_content:
                    doc_copy = doc.copy()
                    doc_copy['content'] = truncated_content
                    doc_copy['_truncated'] = True  # Mark as truncated
                    selected_docs.append(doc_copy)
                    current_tokens += truncator.count_tokens(truncated_content)
            
            break
    
    return selected_docs
