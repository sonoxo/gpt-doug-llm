#!/usr/bin/env python3
"""Build a free, auditable market snapshot using public endpoints and stdlib only."""
from __future__ import annotations
import datetime as dt, json, os, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET

ROOT=os.path.dirname(os.path.dirname(__file__)); OUT=os.path.join(ROOT,"data","market-snapshot.json")
UA={"User-Agent":"gpt-doug-llm market research contact: douglasbrown@24kmediaproductions.com"}
SYMBOLS={"SPY":"S&P 500 ETF","QQQ":"Nasdaq 100 ETF","DIA":"Dow ETF","IWM":"Russell 2000 ETF","GLD":"Gold ETF","TLT":"20Y Treasury ETF","DX-Y.NYB":"US Dollar Index","^VIX":"VIX","AAPL":"Apple","MSFT":"Microsoft","NVDA":"NVIDIA","TSLA":"Tesla","BTC-USD":"Bitcoin","ETH-USD":"Ethereum"}
def get(url,timeout=15):
    req=urllib.request.Request(url,headers=UA); return urllib.request.urlopen(req,timeout=timeout).read()
def quote(symbol,name):
    u="https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(symbol,safe="")+"?range=1mo&interval=1d"
    r=json.loads(get(u))["chart"]["result"][0]; closes=[x for x in r["indicators"]["quote"][0]["close"] if x is not None]
    meta=r["meta"]; price=float(meta.get("regularMarketPrice") or closes[-1]); prev=float(meta.get("chartPreviousClose") or closes[-2]);
    return {"symbol":symbol,"name":name,"price":round(price,4),"change_pct":round((price-prev)/prev*100,3),"history":[round(x,4) for x in closes],"as_of":dt.datetime.fromtimestamp(meta.get("regularMarketTime",time.time()),dt.timezone.utc).isoformat()}
def rss():
    feeds=[("Reuters Business","https://feeds.reuters.com/reuters/businessNews"),("SEC Press","https://www.sec.gov/news/pressreleases.rss")]; out=[]
    for source,url in feeds:
        try:
            root=ET.fromstring(get(url));
            for item in root.findall(".//item")[:8]: out.append({"title":item.findtext("title","").strip(),"url":item.findtext("link","").strip(),"published":item.findtext("pubDate","").strip(),"source":source})
        except Exception: pass
    return out[:12]
def filings():
    out=[]
    try:
        recent=json.loads(get("https://www.sec.gov/submissions/CIK0000320193.json"))["filings"]["recent"]
        for i,form in enumerate(recent["form"]):
            if form not in {"10-K","10-Q","8-K"}: continue
            accession=recent["accessionNumber"][i]; primary=recent["primaryDocument"][i]
            out.append({"ticker":"AAPL","company":"Apple Inc.","form":form,"filed":recent["filingDate"][i],"url":f"https://www.sec.gov/Archives/edgar/data/320193/{accession.replace('-','')}/{primary}"})
            if len(out)>=8: break
    except Exception: pass
    return out
def main():
    quotes=[]; health=[]
    for symbol,name in SYMBOLS.items():
        try: quotes.append(quote(symbol,name))
        except Exception as e: health.append({"name":f"Yahoo {symbol}","status":"error","detail":type(e).__name__})
    news=rss(); sec=filings(); health[:0]=[{"name":"Yahoo Finance charts","status":"ok" if quotes else "error"},{"name":"Public RSS","status":"ok" if news else "degraded"},{"name":"SEC EDGAR","status":"ok" if sec else "degraded"}]
    payload={"schema_version":1,"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"quotes":quotes,"news":news,"filings":sec,"sources":health}
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    with open(OUT,"w",encoding="utf-8") as f: json.dump(payload,f,indent=2)
    if len(quotes)<5: raise SystemExit("insufficient quote coverage")
    print(f"snapshot: {len(quotes)} quotes, {len(news)} headlines, {len(sec)} filings")
if __name__=="__main__": main()
