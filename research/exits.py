"""Stop loss / take profit / cheaper entry on the V3 model. Close-based trigger, executed at the next close. Reported for all settings."""
import sys; sys.path[:0]=["research","."]
import numpy as np, pandas as pd, lab_steady as L
S=L.mat("lgb20",20); N,STEP,KEEP=10,20,30; O={i:L.order(S,i,100) for i in range(L.i0,L.n)}; cf=L.CF.values
lo=L.W("adLow").reindex(L.G).values
def sim(sl=None,tp=None,trail=None,dip=None,cost=.004):
    res=[]; nt=0
    for off in range(0,STEP,5):
        w={};ent={};pk={};cash=1.;todo=None;ex=set();lim={};out=[];ban={}
        for i in range(L.i0+off,L.n):
            v0=sum(w.values())+cash;r=L.R[i]
            for j in w:w[j]*=1+r[j]
            for j in [j for j in w if L.dead[i,j]]:cash+=w.pop(j)*.7
            for j in list(ex):   # exit decided yesterday
                if j in w and r[j]>=-.065 and not L.NT[i,j]:cash+=w.pop(j)*(1-cost/2);ex.discard(j);nt+=1
                elif j not in w:ex.discard(j)
            for j in list(lim):  # waiting limit order, pays the limit price if the low trades through
                if j in w:lim.pop(j);continue
                px,a,d=lim[j]
                if not L.NT[i,j] and lo[i,j]<=px and cash>1e-9:
                    a=min(a,cash);w[j]=a*(1-cost/2)*cf[i,j]/px;cash-=a;ent[j]=pk[j]=px;lim.pop(j)
                elif i>=d:lim.pop(j)
            if todo is not None:
                v=sum(w.values())+cash;rk={j:q+1 for q,j in enumerate(todo)}
                kp=[j for j in w if rk.get(j,999)<=KEEP or r[j]<-.065 or L.NT[i,j]]
                new=[j for j in todo if j not in w and r[j]<=.065 and not L.NT[i,j]][:max(0,N-len(kp))]
                t={j:v/max(N,len(kp)+len(new)) for j in kp}
                for j in w:
                    a=t.get(j,0.)
                    if L.NT[i,j] or (r[j]<-.065 and a<w[j]) or (r[j]>.065 and a>w[j]):t[j]=w[j]
                each=v/max(N,len(kp)+len(new))
                if dip is None:
                    f=min(1,max(0,v-sum(t.values()))/(each*len(new))) if new else 1
                    for j in new:t[j]=each*f;ent[j]=pk[j]=cf[i,j]
                else:
                    lim={j:(cf[i,j]*(1-dip),each,i+STEP-1) for j in new}
                fee=sum(abs(t.get(j,0)-w.get(j,0)) for j in {*t,*w})/2*cost
                w={j:a*(1-fee/v) for j,a in t.items() if a>0};cash=v-fee-sum(w.values());todo=None;ex=set()
            for j in w:
                pk[j]=max(pk.get(j,cf[i,j]),cf[i,j]);g=cf[i,j]/ent.get(j,cf[i,j])-1
                if (sl and g<=-sl) or (tp and g>=tp) or (trail and cf[i,j]/pk[j]-1<=-trail):ex.add(j)
            out.append((sum(w.values())+cash)/v0-1)
            if (i-L.i0-off)%STEP==0:todo=O[i]
        res.append(pd.Series(out,L.G[L.i0+off:]).reindex(L.G[L.i0:]).fillna(0))
    return pd.concat(res,axis=1).mean(axis=1)
def st(s):
    nav=(1+s).cumprod();return dict(CAGR=nav.iloc[-1]**(250/len(s))-1,Sharpe=(s.mean()*250-.04)/s.std()/250**.5,maxDD=(nav/nav.cummax().clip(lower=1)-1).min())
base=None
mon=lambda s:(1+s).groupby(s.index.to_period("M")).prod()-1
T={"none":{},**{f"stop {x:.0%}":dict(sl=x) for x in(.07,.1,.15,.2)},**{f"take {x:.0%}":dict(tp=x) for x in(.1,.15,.2,.3)},**{f"trail {x:.0%}":dict(trail=x) for x in(.1,.15,.2)},"stop10 take20":dict(sl=.1,tp=.2),"stop15 take30":dict(sl=.15,tp=.3),**{f"wait {x:.0%} dip":dict(dip=x) for x in(.02,.03,.05)}}
rows={}
for k,a in T.items():
    s=sim(**a);base=s if base is None else base;o={}
    for n,(x,y) in {"18-22":("2018","2023"),"23-26":("2023","2027")}.items():
        z=s[(s.index>=x)&(s.index<y)];b=base[(base.index>=x)&(base.index<y)];d=mon(z)-mon(b);o.update({f"{q} {n}":v for q,v in st(z).items()});o["t vs none "+n]=d.mean()/d.std()*len(d)**.5 if d.std()>0 else 0
    rows[k]=o
pd.set_option("display.width",250);print(pd.DataFrame(rows).T.round(2).to_string())
F=L.CF.shift(-20)/L.CF-1;hi=L.CF.rolling(20).max().shift(-20)/L.CF-1;lw=L.CF.rolling(20).min().shift(-20)/L.CF-1
for x,y in(("2018","2023"),("2023","2027")):
    q=[[A.values[i][O[i][:10]] for i in range(L.i0,L.n-20) if pd.Timestamp(x)<=L.G[i]<pd.Timestamp(y)] for A in(F,hi,lw)]
    print(x,{n:np.nanquantile(np.concatenate(v),[.1,.25,.5,.75,.9]).round(3).tolist() for n,v in zip(("20d return","highest close","lowest close"),q)})
