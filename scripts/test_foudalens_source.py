#!/usr/bin/env python3
"""Read-only connectivity test for a public trading summary page."""
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser

URL = 'https://foudalens.com/en/trading-summary'

class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.hidden:
            self.hidden -= 1
    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())

print('Checking public trading-summary page:', URL)
request = urllib.request.Request(URL, headers={
    'User-Agent': 'EgyptDebtFXIntelligence/1.0 (public read-only data availability test)',
    'Accept': 'text/html,application/xhtml+xml',
})
try:
    with urllib.request.urlopen(request, timeout=25) as response:
        status = response.status
        content = response.read(2_000_000).decode('utf-8', errors='replace')
        print('HTTP status:', status)
        print('Downloaded characters:', len(content))
except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
    print('FAILED: Automated access was unsuccessful:', exc)
    raise SystemExit(1)

parser = PageText()
parser.feed(content)
text = ' '.join(parser.parts)
keywords = ['foreign', 'arab', 'treasury', 'bond', 'bill', 'أجانب', 'عرب', 'أذون', 'سندات']
found = [word for word in keywords if word.casefold() in text.casefold()]
print('Visible-text keywords found:', ', '.join(found) or 'none')
print('Visible-text length:', len(text))
print('HTML table tags:', len(re.findall(r'<table\b', content, re.I)))
if not found:
    print('WARNING: Page is reachable, but trading data may be loaded dynamically by JavaScript.')
    raise SystemExit(2)
print('SUCCESS: Page is reachable and relevant words appear in server response.')
print('NOTE: This does not yet verify numerical data accuracy or extraction.')
