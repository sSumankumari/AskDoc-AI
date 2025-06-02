import requests
import logging
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin
from config import get_config

logger = logging.getLogger(__name__)


class WebScraper:
    """
    Enhanced web scraper with better content extraction
    """

    def __init__(self):
        config = get_config()
        self.timeout = config.REQUEST_TIMEOUT
        self.max_url_length = config.MAX_URL_LENGTH

        # Common headers to avoid blocking
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

    def validate_url(self, url: str) -> bool:
        """
        Validate URL format and length
        """
        if not url or len(url) > self.max_url_length:
            return False

        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def scrape_url_content(self, url: str) -> Dict[str, Any]:
        """
        Enhanced URL scraping with better content extraction
        """
        if not self.validate_url(url):
            raise ValueError("Invalid URL provided")

        try:
            logger.info(f"Scraping content from: {url}")

            # Make the request
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "No title"

            # Extract main content
            content = self._extract_main_content(soup)

            # Extract metadata
            metadata = self._extract_metadata(soup, url)

            if not content.strip():
                raise ValueError("No readable content found on the webpage")

            logger.info(f"Successfully extracted {len(content)} characters from {url}")

            return {
                'content': content,
                'title': title_text,
                'url': url,
                'metadata': metadata,
                'word_count': len(content.split()),
                'char_count': len(content)
            }

        except requests.exceptions.Timeout:
            raise Exception(f"Request timeout while accessing {url}")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Connection error while accessing {url}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP error {e.response.status_code} while accessing {url}")
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            raise Exception(f"Failed to scrape content from {url}: {str(e)}")

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content using multiple strategies
        """
        content_parts = []

        # Strategy 1: Look for main content containers
        main_selectors = [
            'main', 'article', '[role="main"]',
            '.content', '#content', '.post-content',
            '.entry-content', '.article-content'
        ]

        for selector in main_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                content_parts.append(self._extract_text_from_element(main_content))
                break

        # Strategy 2: Extract paragraphs if no main content found
        if not content_parts:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 20:  # Only include substantial paragraphs
                    content_parts.append(text)

        # Strategy 3: Fallback to div elements with substantial text
        if not content_parts:
            divs = soup.find_all('div')
            for div in divs:
                text = div.get_text().strip()
                if len(text) > 100 and len(text.split()) > 20:
                    content_parts.append(text)

        return '\n\n'.join(content_parts)

    def _extract_text_from_element(self, element) -> str:
        """
        Extract clean text from an HTML element
        """
        # Get text and clean it up
        text = element.get_text(separator='\n')

        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines

        return '\n'.join(lines)

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract metadata from the webpage
        """
        metadata = {'source_url': url}

        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            metadata['description'] = meta_desc.get('content', '')

        # Extract meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            metadata['keywords'] = meta_keywords.get('content', '')

        # Extract author
        author = soup.find('meta', attrs={'name': 'author'})
        if author:
            metadata['author'] = author.get('content', '')

        # Extract publication date
        pub_date = soup.find('meta', attrs={'property': 'article:published_time'})
        if not pub_date:
            pub_date = soup.find('meta', attrs={'name': 'date'})
        if pub_date:
            metadata['published_date'] = pub_date.get('content', '')

        return metadata


# Convenience function for backward compatibility
def scrape_url_content(url: str) -> str:
    """
    Simple function that returns just the content text
    """
    scraper = WebScraper()
    result = scraper.scrape_url_content(url)
    return result['content']