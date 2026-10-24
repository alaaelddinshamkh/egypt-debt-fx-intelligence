"""Safely merge CBE historical USD/EGP Excel data into existing JSON.

Usage: python scripts/update_fx.py --excel 'historical data.xlsx'
Requires: pip install openpyxl
"""
import argparse
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from openpyxl import load_workbook

DATA_FILE = Path('data/fx_history.json')


def parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        return date(1899, 12, 30) + timedelta(days=int(value))
    if isinstance(value, str):
        for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                pass
    raise ValueError(f'Unrecognized date: {value!r}')


def read_excel(path):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if 'Market Exchange Rates' not in workbook.sheetnames:
            raise ValueError('Missing worksheet: Market Exchange Rates')
        sheet = workbook['Market Exchange Rates']
        if [sheet['A2'].value, sheet['B2'].value] != ['Date', 'Weighted Avg.']:
            raise ValueError('Unexpected Excel column headings')
        incoming = {}
        for row in sheet.iter_rows(min_row=3, max_col=2, values_only=True):
            day_raw, rate_raw = row
            if day_raw is None and rate_raw is None:
                continue
            day = parse_date(day_raw).isoformat()
            rate = float(rate_raw)
            if not math.isfinite(rate) or not 1 <= rate <= 500:
                raise ValueError(f'Invalid rate on {day}: {rate_raw!r}')
            if day in incoming and incoming[day] != rate:
                raise ValueError(f'Conflicting rates for {day}')
            incoming[day] = rate
        if not incoming:
            raise ValueError('Excel contains no exchange rates')
        return incoming
    finally:
        workbook.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--excel', required=True, type=Path)
    parser.add_argument('--apply', action='store_true', help='Write changes; default is preview only')
    args = parser.parse_args()
    if not DATA_FILE.is_file():
        raise FileNotFoundError(DATA_FILE)
    with DATA_FILE.open(encoding='utf-8') as handle:
        data = json.load(handle)
    records = data.get('records')
    if not isinstance(records, list) or not records:
        raise ValueError('Existing JSON records missing or empty')
    existing = {}
    for record in records:
        day = record['date']
        if day in existing:
            raise ValueError(f'Duplicate existing date: {day}')
        existing[day] = record
    incoming = read_excel(args.excel)
    conflicts = [(day, existing[day]['usd_egp_weighted_avg'], rate)
                 for day, rate in incoming.items()
                 if day in existing and not math.isclose(float(existing[day]['usd_egp_weighted_avg']), rate, abs_tol=0.00005)]
    if conflicts:
        raise ValueError(f'Existing values differ from Excel; refusing overwrite: {conflicts[:5]}')
    additions = [{'date': day, 'usd_egp_weighted_avg': rate}
                 for day, rate in sorted(incoming.items()) if day not in existing]
    print(f'Existing: {len(records)} | Excel: {len(incoming)} | New: {len(additions)}')
    if not args.apply:
        print('PREVIEW ONLY: no files changed. Use --apply after review.')
        print('New rows:', additions[:10])
        return
    if not additions:
        print('No changes needed.')
        return
    data['records'] = sorted(records + additions, key=lambda item: item['date'])
    data['count'] = len(data['records'])
    data['date_min'] = data['records'][0]['date']
    data['date_max'] = data['records'][-1]['date']
    temp = DATA_FILE.with_suffix('.json.tmp')
    with temp.open('w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    temp.replace(DATA_FILE)
    print('Updated JSON successfully.')


if __name__ == '__main__':
    main()
