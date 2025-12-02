"""
Parse llms.txt files to extract documentation links
"""
import re
from urllib.parse import urljoin, urlparse
from typing import List, Dict


def parse_llms_txt(content: str, base_url: str) -> List[Dict]:
    """
    Parse llms.txt and extract doc URLs
    
    Format examples:
    - [Title](url): Description
    - [Title](url)
    - [Title](https://full-url.com/path)
    
    Args:
        content: Raw llms.txt content
        base_url: Base URL for resolving relative links (e.g., https://docs.privy.io)
    
    Returns:
        List of dicts with title, url, description, path
    """
    doc_links = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Match markdown links: [text](url)
        match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line)
        if match:
            title = match.group(1)
            url = match.group(2)
            
            # Skip if it's not a valid URL (e.g., anchors, special links)
            if url.startswith('#') or url.startswith('mailto:') or url.startswith('javascript:'):
                continue
            
            # Handle relative URLs
            full_url = urljoin(base_url, url)
            
            # Extract description (everything after colon, if present)
            description = ''
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    description = parts[1].strip()
            
            parsed_url = urlparse(full_url)
            
            doc_links.append({
                'title': title,
                'url': full_url,
                'description': description,
                'path': parsed_url.path,
                'domain': parsed_url.netloc
            })
    
    return doc_links


async def fetch_llms_txt(base_url: str) -> str:
    """
    Fetch llms.txt from docs site
    
    Args:
        base_url: Base URL (e.g., https://docs.privy.io)
    
    Returns:
        Raw llms.txt content
    """
    import aiohttp
    
    llms_url = f"{base_url.rstrip('/')}/llms.txt"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(llms_url, timeout=10) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch llms.txt: {response.status}")
            return await response.text()

