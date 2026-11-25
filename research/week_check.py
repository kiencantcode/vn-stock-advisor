"""How informative is one week? Top 6 bought next session (limit at last close else close), value after holding 5 sessions, 0.4% cost."""
import sys; sys.path[:0]=["research","."]
import numpy as np, pandas as pd, lab_steady as L, lab_all as A
S=L.mat("lgb20",20); cf=L.cf if hasattr(L,"cf") else L.CF.values; E=L.etf.reindex(L.G).ffill().values; r=[]
x=L.x; v20=(L.CF.pct_change(fill_method=None).rolling(20).std()).values; LQ=L.LQ<=100; z=np.where(LQ,(L.CF.shift(-6).values/cf-1)/(v20*6**.5),np.nan)
for i in range(L.i0+260,L.n-6):
    o=L.order(S,i,100)
    b=[j for j in o if not L.NT[i+1,j] and L.R[i+1,j]<=.065][:6]; p=[min(A.OP[i+1,j],cf[i,j]) if A.LO[i+1,j]<=cf[i,j] else cf[i+1,j] for j in b]
    g=np.array([cf[i+6,j]/q-1 for j,q in zip(b,p)])-.004; al=np.nanmean(cf[i+6,o]/cf[i+1,o]-1)
    w=z[max(0,i-256):i-5]; w=w[np.isfinite(w)]; lo,hi=np.quantile(w,[.1,.9]); t=o[:6]; y=cf[i+6,t]/cf[i,t]-1; s=v20[i,t]*6**.5
    r.append((L.G[i],g.mean(),E[i+6]/E[i+1]-1,al,np.mean(g>0),np.mean((y>=lo*s)&(y<=hi*s))))
d=pd.DataFrame(r,columns=["d","m","f","a","up","cov"]).set_index("d")
for a,b in(("2019","2023"),("2023","2027")):
    q=d[(d.index>=a)&(d.index<b)]; e=q.m-q.f
    n5=[(q.iloc[k::5].m-q.iloc[k::5].f) for k in range(5)]; mu,sd=e.mean(),e.std()
    print(a,"mean week %.2f%% fund %.2f%% all %.2f%%"%(q.m.mean()*100,q.f.mean()*100,q.a.mean()*100),"weeks>0 %.3f beat fund %.3f beat all %.3f; picks up %.3f; range cov %.3f"%((q.m>0).mean(),(e>0).mean(),(q.m>q.a).mean(),q.up.mean(),q["cov"].mean()),"excess sd %.2f%%, weeks for t=1.65: %.0f; worst week %.1f%%, p10 %.1f%%"%(sd*100,(1.65*sd/mu)**2 if mu>0 else np.inf,q.m.min()*100,q.m.quantile(.1)*100))
    nx=[]
    for k in range(5):
        w=q.iloc[k::5]; nx.append((w.m.shift(-1)-w.f.shift(-1)).groupby((w.m>w.f)).mean())
    print(" next-week excess after a winning / losing week:",pd.concat(nx,axis=1).mean(axis=1).mul(100).round(2).to_dict())
