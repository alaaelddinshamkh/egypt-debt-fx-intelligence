"""Fetch indicative USD/EGP buy/sell benchmark from Daleelak.

Run from repository root:
    python scripts/update_live_fx.py          # preview
    python scripts/update_live_fx.py --apply  # save data/fx_live.json

Uses only Python standard library. Does not modify CBE historical records.
"""
import argparse
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

API_URL = 'https://getdaleelak.com/api/v1/feed.json'
OUTPUT = Path('data/fx_live.json')


def get_data():
    request = Request(API_URL, headers={'User-Agent': 'EgyptDebtFXIntelligence/1.0', 'Accept': 'application/json'})
    with urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError(f'API HTTP {response.status}')
        return json.load(response)


def positive_rate(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be numeric')
    value = float(value)
    if not math.isfinite(value) or not 1 <= value <= 500:
        raise ValueError(f'{name} is out of range: {value}')
    return value


def parse_utc(value, name):
    if not isinstance(value, str):
        raise ValueError(f'Missing {name}')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError(f'{name} lacks timezone')
    return parsed.astimezone(timezone.utc)


def transform(payload):
    assets = payload.get('assets')
    if not isinstance(assets, list):
        raise ValueError('Missing assets array')
    matches = [asset for asset in assets if isinstance(asset, dict) and asset.get('id') == 'USD-EGP']
    if len(matches) != 1:
        raise ValueError(f'Expected one USD-EGP asset, found {len(matches)}')
    asset = matches[0]
    benchmark = asset.get('benchmark')
    if not isinstance(benchmark, dict):
        raise ValueError('Missing USD-EGP benchmark')
    buy = positive_rate(benchmark.get('buy'), 'benchmark.buy')
    sell = positive_rate(benchmark.get('sell'), 'benchmark.sell')
    if buy > sell:
        raise ValueError('Buy price exceeds sell price')
    observed = parse_utc(asset.get('observedAt'), 'observedAt')
    generated = parse_utc(payload.get('generatedAt'), 'generatedAt')
    now = datetime.now(timezone.utc)
    if observed > now.replace(microsecond=0) and (observed - now).total_seconds() > 600:
        raise ValueError('Observation timestamp is in the future')
    if (now - observed).total_seconds() > 72 * 3600:
        raise ValueError('USD-EGP observation older than 72 hours; refusing stale update')
    if generated > now and (generated - now).total_seconds() > 600:
        raise ValueError('Feed generatedAt is in the future')
    as_of = asset.get('asOf')
    if not isinstance(as_of, str) or len(as_of) != 10:
        raise ValueError('Invalid asOf')
    datetime.strptime(as_of, '%Y-%m-%d')
    return {
        'pair': 'USD/EGP',
        'buy': buy,
        'sell': sell,
        'as_of': as_of,
        'observed_at': observed.isoformat().replace('+00:00', 'Z'),
        'feed_generated_at': generated.isoformat().replace('+00:00', 'Z'),
        'fetched_at': now.isoformat().replace('+00:00', 'Z'),
        'source': 'Daleelak',
        'source_url': API_URL,
        'price_type': 'third_party_indicative_benchmark',
        'is_official_cbe_rate': False,
        'note': 'Indicative third-party benchmark; not verified as an official CBE quote.',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Save JSON; otherwise preview only')
    args = parser.parse_args()
    data = transform(get_data())
    print(json.dumps(data, ensure_ascii=False, indent=2))
    if not args.apply:
        print('PREVIEW ONLY: no file changed. Add --apply to save.')
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        previous = json.loads(OUTPUT.read_text(encoding='utf-8'))
        previous_time = previous.get('observed_at')
        if previous_time and parse_utc(previous_time, 'previous observed_at') > parse_utc(data['observed_at'], 'observed_at'):
            raise ValueError('Incoming quote is older than saved quote; refusing overwrite')
        if previous.get('observed_at') == data['observed_at'] and previous.get('buy') == data['buy'] and previous.get('sell') == data['sell']:
            print('No new quote; leaving existing file unchanged.')
            return
    fd, temp_name = tempfile.mkstemp(prefix='.fx_live_', suffix='.tmp', dir=OUTPUT.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(temp_name, OUTPUT)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    print(f'Saved {OUTPUT}')


if __name__ == '__main__':
    main()
