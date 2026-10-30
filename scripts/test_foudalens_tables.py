#!/usr/bin/env python3
"""Read-only diagnostic: inspect public HTML tables, without saving or assuming figures."""
import re
import urllib.request
from html.parser import HTMLParser

URL = 'https://foudalens.com/en/trading-summary'

class TableReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.depth = 0
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            if self.depth == 0:
                self.table = []
            self.depth += 1
        elif self.depth and tag == 'tr':
            self.row = []
        elif self.depth and tag in ('td', 'th') and self.row is not None:
            self.cell = []
    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None and self.row is not None:
            self.row.append(re.sub(r'\s+', ' ', ''.join(self.cell)).strip())
            self.cell = None
        elif tag == 'tr' and self.row is not None and self.table is not None:
            if any(self.row):
                self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.depth:
            self.depth -= 1
            if self.depth == 0:
                self.tables.append(self.table)
                self.table = None

print('Reading:', URL)
req = urllib.request.Request(URL, headers={'User-Agent': 'EgyptDebtFXIntelligence/1.0 (public data test)', 'Accept': 'text/html'})
try:
    with urllib.request.urlopen(req, timeout=25) as response:
        html = response.read(2_000_000).decode('utf-8', errors='replace')
        print('HTTP:', response.status)
except Exception as exc:
    print('FAILED: Could not load page:', exc)
    raise SystemExit(1)
reader = TableReader()
reader.feed(html)
print('TABLE COUNT:', len(reader.tables))
for i, table in enumerate(reader.tables, 1):
    print(f'\nTABLE {i}: {len(table)} rows')
    for row in table[:15]:
        print(' | '.join(cell[:110] for cell in row[:12])[:900])
    if len(table) > 15:
        print(f'... {len(table)-15} additional rows not shown')
if not reader.tables or not any(reader.tables):
    print('WARNING: No populated HTML tables; data may be elsewhere in the page.')
else:
    print('\nDONE: Tables inspected; numeric accuracy still requires verification.')
