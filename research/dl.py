import requests,pandas as pd,time,os
from concurrent.futures import ThreadPoolExecutor
H={"User-Agent":"Mozilla/5.0"};B="https://api-finfo.vndirect.com.vn/v4/"
def q(p,**k):
    for a in range(5):
        try:
            r=requests.get(B+p,params=k,headers=H,timeout=60)
            if r.status_code==200: j=r.json();return pd.DataFrame(j["data"]),j.get("totalPages",1)
        except Exception as e: pass
        time.sleep(2*(a+1))
    return None,0
L,_=q("stocks",q="type:STOCK~floor:HOSE",size=3000);L.to_pickle("list.pkl");S=sorted(L.code.unique())
def px(s):
    d,n=q("stock_prices",q=f"code:{s}",size=5000,sort="date")
    if d is None or d.empty: return s,None
    return s,d[[c for c in("code","date","open","high","low","close","adOpen","adHigh","adLow","adClose","nmVolume","nmValue","floor") if c in d]]
# items: net profit parent & total, equity, shares etc chosen later: store income+balance key codes
def fs(s):
    out=[]
    for pg in (1,2):
        d,n=q("financial_statements",q=f"code:{s}~reportType:QUARTER~modelType:1,2,89,90,101,102,411,412",size=20000,page=pg)
        if d is None: return s,None
        out.append(d)
        if pg>=n: break
    d=pd.concat(out);return s,d
with ThreadPoolExecutor(4) as ex: P=list(ex.map(px,S))
print("px",sum(d is not None for _,d in P),[s for s,d in P if d is None]);pd.concat([d for _,d in P if d is not None]).to_pickle("px.pkl")
with ThreadPoolExecutor(4) as ex: Fs=list(ex.map(fs,S))
print("fs",sum(d is not None and len(d)>0 for _,d in Fs),[s for s,d in Fs if d is None or d.empty]);pd.concat([d for _,d in Fs if d is not None and len(d)]).to_pickle("fs.pkl")
