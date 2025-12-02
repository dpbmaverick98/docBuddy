"""
Fetch documentation content from URLs
"""
import aiohttp
import asyncio
from typing import List, Dict, Optional
from html2text import html2text


def is_markdown_content(content: str) -> bool:
    """
    Check if content is already markdown (not HTML)
    
    Args:
        content: Raw content from response
    
    Returns:
        True if content appears to be markdown
    """
    content_stripped = content.strip()
    
    # Markdown indicators:
    # 1. Starts with # (heading)
    # 2. Contains markdown patterns but no HTML tags
    # 3. No <html>, <body>, <div> tags (or very few)
    
    if content_stripped.startswith('#'):
        return True
    
    # Check for HTML tags
    html_tag_count = content.count('<html') + content.count('<body') + content.count('<div')
    markdown_patterns = content.count('##') + content.count('```') + content.count('[')
    
    # If it has markdown patterns but few/no HTML tags, it's likely markdown
    if markdown_patterns > 3 and html_tag_count < 5:
        return True
    
    return False


async def fetch_doc_content(
    session: aiohttp.ClientSession,
    doc_info: Dict,
    timeout: int = 10
) -> Dict:
    """
    Fetch individual doc page content
    
    Args:
        session: aiohttp session
        doc_info: Dict with url, title, path, etc.
        timeout: Request timeout in seconds
    
    Returns:
        Dict with doc info + content + status
    """
    try:
        async with session.get(doc_info['url'], timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            if response.status == 200:
                content = await response.text()
                
                # Check if content is already markdown (starts with # or common markdown patterns)
                # Some docs sites serve raw .md files
                if is_markdown_content(content):
                    markdown_content = content
                else:
                    # Try to extract markdown from HTML
                    markdown_content = extract_markdown_from_html(content, doc_info['url'])
                
                return {
                    **doc_info,
                    'content': markdown_content,
                    'status': 'success',
                    'content_length': len(markdown_content)
                }
            else:
                return {
                    **doc_info,
                    'content': '',
                    'status': f'error_{response.status}',
                    'error': f'HTTP {response.status}'
                }
    except asyncio.TimeoutError:
        return {
            **doc_info,
            'content': '',
            'status': 'timeout',
            'error': 'Request timeout'
        }
    except Exception as e:
        return {
            **doc_info,
            'content': '',
            'status': 'error',
            'error': str(e)
        }


def extract_markdown_from_html(html: str, url: str) -> str:
    """
    Extract markdown content from HTML docs page
    
    Uses html2text to convert HTML to markdown.
    Most docs sites have a main content area.
    
    Args:
        html: HTML content
        url: Original URL (for context)
    
    Returns:
        Markdown content
    """
    from bs4 import BeautifulSoup
    import html2text
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find main content area (common patterns)
    content_selectors = [
        'main',
        'article',
        '.content',
        '.doc-content',
        '[role="main"]',
        '.markdown-body',  # GitHub-style
    ]
    
    content = None
    for selector in content_selectors:
        content = soup.select_one(selector)
        if content:
            break
    
    # Fallback to body if no main content found
    if not content:
        content = soup.find('body')
    
    if content:
        # Convert HTML to markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0  # Don't wrap lines
        
        markdown = h.handle(str(content))
        return markdown.strip()
    
    return ""


async def fetch_all_docs(
    doc_links: List[Dict],
    max_concurrent: int = 20,
    timeout: int = 10
) -> List[Dict]:
    """
    Fetch all docs in parallel with rate limiting
    
    Args:
        doc_links: List of doc info dicts
        max_concurrent: Max parallel requests
        timeout: Request timeout per doc
    
    Returns:
        List of successfully fetched docs
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_with_limit(doc_info: Dict):
        async with semaphore:
            return await fetch_doc_content(session, doc_info, timeout)
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_with_limit(doc) for doc in doc_links]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        successful = []
        failed = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append({
                    **doc_links[i],
                    'status': 'exception',
                    'error': str(result)
                })
            elif result.get('status') == 'success':
                successful.append(result)
            else:
                failed.append(result)
        
        if failed:
            print(f"\n⚠️  Failed to fetch {len(failed)} docs:")
            for f in failed[:5]:  # Show first 5 failures
                print(f"  - {f.get('title', 'Unknown')}: {f.get('error', f.get('status'))}")
            if len(failed) > 5:
                print(f"  ... and {len(failed) - 5} more")
        
        return successful

