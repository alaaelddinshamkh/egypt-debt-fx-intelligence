#!/usr/bin/env python3
"""Conservative public-page net debt flow extractor. Values are EGP millions."""
import argparse, datetime as dt, json, re, urllib.request
from pathlib import Path
from html.parser import HTMLParser

URL='https://foudalens.com/en/trading-summary'
OUT=Path('data/debt_flows.json')
class Text(HTMLParser):
    def __init__(self): super().__init__(); self.bits=[]; self.skip=0
    def handle_starttag(self,t,a):
        if t in ('script','style'): self.skip+=1
    def handle_endtag(self,t):
        if t in ('script','style') and self.skip:self.skip-=1
    def handle_data(self,s):
        if not self.skip and s.strip():self.bits.append(re.sub(r'\s+',' ',s).strip())

def amount(s):
    s=s.strip().replace(',','').replace('−','-').replace('–','-').replace('＋','+')
    m=re.fullmatch(r'([+-]?)\s*(\d+(?:\.\d+)?)\s*([BMK]?)',s,re.I)
    if not m: return None
    n=float(m.group(2))*{'B':1000,'M':1,'K':0.001,'':1/1_000_000}[m.group(3).upper()]
    return round((-1 if m.group(1)=='-' else 1)*n,5)

def find_date(txt):
    m=re.search(r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d\d)\b',txt,re.I)
    if not m: raise ValueError('Session date not found; refusing to guess')
    return dt.datetime.strptime(' '.join(m.groups()),'%d %B %Y').date().isoformat()

def extract(bits):
    joined=' '.join(bits)
    day=find_date(joined)
    # Only the instrument-specific section; never confuse total-market nationality net with debt net.
    i=next((i for i,x in enumerate(bits) if x.strip().lower()=='by instrument type'),None)
    if i is None: raise ValueError('By instrument type section missing')
    tail=bits[i+1:]
    stop=next((i for i,x in enumerate(tail) if x.lower().startswith('source:')),len(tail))
    tail=tail[:stop]
    out={}
    for label,code in [('Bonds','bond'),('Treasury bills','tbill')]:
        start=next((i for i,x in enumerate(tail) if x.lower()==label.lower()),None)
        if start is None: raise ValueError(f'{label} heading missing')
        end=next((i for i in range(start+1,len(tail)) if tail[i].lower() in ('stocks','bonds','treasury bills')),len(tail))
        segment=tail[start+1:end]
        found={}
        for j,token in enumerate(segment):
            for nationality,code_n in [('Arabs','arab'),('Foreigners','foreign')]:
                # Accept labels only when the adjacent value is an unambiguous number.
                if token.lower()==nationality.lower() and j+1<len(segment):
                    val=amount(segment[j+1])
                    if val is not None: found[code_n]=val
                elif token.lower().startswith(nationality.lower()) and token.lower()!=nationality.lower():
                    val=amount(token[len(nationality):])
                    if val is not None: found[code_n]=val
        if set(found)!={'arab','foreign'}: raise ValueError(f'Cannot unambiguously parse {label}: {segment[:30]}')
        for n,v in found.items():out[(code,n)]=v
    if len(out)!=4:raise ValueError('Expected four instrument/nationality pairs')
    return day,out

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
    req=urllib.request.Request(URL,headers={'User-Agent':'EgyptDebtFXIntelligence/1.0','Accept':'text/html'})
    with urllib.request.urlopen(req,timeout=30) as r:
        if r.status!=200:raise RuntimeError(f'HTTP {r.status}')
        html=r.read(3_000_000).decode('utf-8','replace')
    parser=Text();parser.feed(html)
    day,flows=extract(parser.bits)
    old={'schema_version':1,'source':'FoudaLens','source_url':URL,'unit':'EGP_million','records':[]}
    if OUT.exists():
        old=json.loads(OUT.read_text(encoding='utf-8'))
        if old.get('unit')!='EGP_million' or not isinstance(old.get('records'),list):raise ValueError('Existing JSON format incompatible')
    records=[r for r in old['records'] if r.get('date')!=day]
    for (instrument,investor),net in sorted(flows.items()):
        records.append({'date':day,'type':'secondary','investor':investor,'instrument':instrument,'net_egp_million':net,'source':URL,'measure':'net_buy_minus_sell','data_origin':'third_party_egx_attribution'})
    records.sort(key=lambda x:(x['date'],x['instrument'],x['investor']))
    # Keep the latest known session even if the provider temporarily serves an older date.
    latest_session=max(r['date'] for r in records)
    result={**old,'records':records,'latest_session':latest_session,'note':'Net securities trading in EGP millions, not actual FX outflow; third-party reported EGX data. Gross buy/sell by instrument not provided.'}
    print('Session:',day,'values (EGP million):',flows,'total records:',len(records))
    if args.apply:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if not OUT.exists() or OUT.read_text(encoding='utf-8')!=text:
            OUT.write_text(text,encoding='utf-8');print('UPDATED',OUT)
        else:print('UNCHANGED',OUT)
    else:print('PREVIEW only; add --apply to write')
if __name__=='__main__':main()
