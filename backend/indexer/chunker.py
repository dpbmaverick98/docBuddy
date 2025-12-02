"""
Simple markdown chunker - split by headings
No LangChain, fully debuggable
"""
from typing import List, Dict
import re


def split_by_headings(md_content: str, doc_path: str, min_chunk_size: int = 100) -> List[Dict]:
    """
    Split markdown by H2 headings (##)
    
    Simple, debuggable approach. Each H2 section becomes a chunk.
    Preserves heading hierarchy for context.
    
    Args:
        md_content: Raw markdown content
        doc_path: Path/URL of the document
        min_chunk_size: Minimum chunk size in characters (filters tiny chunks)
    
    Returns:
        List of chunks with heading, content, level, etc.
    """
    chunks = []
    lines = md_content.split('\n')
    
    current_heading = "Introduction"
    current_content = []
    heading_level = 0
    chunk_index = 0
    
    for line in lines:
        # Check if it's a heading
        if line.startswith('#'):
            # Save previous chunk if it has content
            if current_content and len('\n'.join(current_content)) >= min_chunk_size:
                chunks.append({
                    'heading': current_heading,
                    'content': '\n'.join(current_content).strip(),
                    'doc_path': doc_path,
                    'level': heading_level,
                    'chunk_index': chunk_index
                })
                chunk_index += 1
            
            # Start new chunk
            heading_level = len(line) - len(line.lstrip('#'))
            current_heading = line.lstrip('#').strip()
            current_content = []
        else:
            current_content.append(line)
    
    # Don't forget the last chunk
    if current_content and len('\n'.join(current_content)) >= min_chunk_size:
        chunks.append({
            'heading': current_heading,
            'content': '\n'.join(current_content).strip(),
            'doc_path': doc_path,
            'level': heading_level,
            'chunk_index': chunk_index
        })
    
    # If no headings found, create one chunk from entire content
    if not chunks and md_content.strip():
        chunks.append({
            'heading': 'Content',
            'content': md_content.strip(),
            'doc_path': doc_path,
            'level': 0,
            'chunk_index': 0
        })
    
    return chunks


def get_chunk_stats(chunks: List[Dict]) -> Dict:
    """
    Get statistics about chunks for verification
    
    Returns:
        Dict with stats: total_chunks, avg_size, min_size, max_size, etc.
    """
    if not chunks:
        return {
            'total_chunks': 0,
            'avg_size': 0,
            'min_size': 0,
            'max_size': 0,
            'total_chars': 0
        }
    
    sizes = [len(chunk['content']) for chunk in chunks]
    
    return {
        'total_chunks': len(chunks),
        'avg_size': sum(sizes) / len(sizes),
        'min_size': min(sizes),
        'max_size': max(sizes),
        'total_chars': sum(sizes),
        'headings': [chunk['heading'] for chunk in chunks[:10]]  # First 10 headings
    }

