"""Test automated access to a public news listing (no data is written)."""
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
import sys

URL = 'https://www.cairo24.com/keyword/1215270'

class ArticleLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()
    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        href = dict(attrs).get('href', '')
        absolute = urljoin(URL, href)
        parsed = urlparse(absolute)
        if parsed.netloc in ('www.cairo24.com', 'cairo24.com') and parsed.path.strip('/').isdigit():
            self.links.add(absolute.split('?')[0])

def main():
    print('Checking:', URL)
    req = Request(URL, headers={'User-Agent': 'Mozilla/5.0 (compatible; DebtFXMonitor/1.0)', 'Accept': 'text/html'})
    try:
        with urlopen(req, timeout=25) as response:
            status = response.status
            body = response.read(3_000_000)
            content_type = response.headers.get('Content-Type', '')
    except (HTTPError, URLError, TimeoutError) as exc:
        print('FAILED: Cannot fetch source:', exc)
        return 1
    print('HTTP status:', status)
    print('Content type:', content_type)
    if 'html' not in content_type.lower():
        print('FAILED: Response is not HTML')
        return 1
    parser = ArticleLinks()
    parser.feed(body.decode('utf-8', errors='replace'))
    print('Article links found:', len(parser.links))
    for link in sorted(parser.links)[:5]:
        print(' -', link)
    if not parser.links:
        print('FAILED: No article links found. Page may be blocked or dynamically rendered.')
        return 1
    print('SUCCESS: Automated source access and article link discovery work.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
