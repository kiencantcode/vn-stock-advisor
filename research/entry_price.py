"""One concrete buy price. Choose on 2018-22, check on 2023-26. Event study, top picks, 0.4% cost, limit filled at the limit (or the open if lower)."""
import sys; sys.path[:0]=["research","."]
import numpy as np, pandas as pd
from advisor import data, features, model, pipeline, track
cfg=pipeline.load_config(); core={s for v in cfg["sectors"].values() for s in v}
fr,_=data.load_many([*core,*cfg["train_extra"]],4900,"auto"); x=features.build_panel(fr,data.load("VNINDEX",4900,"auto"),5)
D=np.sort(x["date"].unique()); o=model.walk_forward(x,core,5,"2018-01-01"); o["rk"]=o.groupby("date")["score"].rank(ascending=False,method="first"); o=o[o.rk<=6]
q=pd.DataFrame({d:model.conformal(x,d,5)["y_low"] for d in o["date"].unique()}).T; o["q5"]=o["date"].map(q[0.5])
A={s:d.set_index("date") for s,d in fr.items()}; rows=[]
for r in o[["date","sym","close","vol20","q5"]].itertuples():
    d=A[r.sym]; i=d.index.get_loc(r.date)
    if i+6>=len(d): continue
    f=d.iloc[i+1:i+7]; C=r.close; ex=f.close.iloc[4]; b={"date":r.date}
    b["mua giá mở cửa"]=ex/f.open.iloc[0]-1-.004 if f.open.iloc[0]<C*1.065 else np.nan
    b["mua giá đóng cửa hôm sau"]=ex/f.close.iloc[0]-1-.004
    sg=r.vol20*5**.5
    for nm,L,n in (("đặt giá đóng cửa, 1 phiên",C,1),("đặt giá đóng cửa, 3 phiên",C,3),("đặt -1%, 3 phiên",C*.99,3),("đặt -2%, 3 phiên",C*.98,3),("đáy vùng mua, 5 phiên",C*(1+r.q5*sg),4),("giữa vùng mua, 3 phiên",C*(1+r.q5*sg/2),3)):
        v=np.nan
        for k in range(n):
            if f.low.iloc[k]<=L: v=ex/min(L,f.open.iloc[k])-1-.004;break
        b[nm]=v
    rows.append(b)
z=pd.DataFrame(rows).set_index("date")
for a,e in(("2018","2023"),("2023","2027")):
    g=z[(z.index>=a)&(z.index<e)];t={}
    for c in z:
        m=g[c].fillna(0).groupby(level=0).mean();bm=g["mua giá mở cửa"].fillna(0).groupby(level=0).mean();t[c]=dict(khop=g[c].notna().mean(),lai_moi_lenh_dat=m.mean()*100,lai_khi_khop=g[c].mean()*100,t_vs_mo_cua=track._nw_t(m-bm,4))
    print(a);print(pd.DataFrame(t).T.round(3).to_string())
import lab_steady as L
S=L.mat("lgb20",20);W={k:L.W(k).reindex(L.G).values for k in("adOpen","adLow")};cf=L.CF.values;out=[]
for i in range(L.i0,L.n-22):
    for j in L.order(S,i,100)[:10]:
        if L.NT[i+1,j] or L.R[i+1,j]>.065: continue
        c0,c1,op,lw,e=cf[i,j],cf[i+1,j],W["adOpen"][i+1,j],W["adLow"][i+1,j],cf[i+21,j];b=dict(date=L.G[i],close=e/c1-1,open=e/op-1)
        for nm,k in(("lim0",1),("lim1",.99),("lim2",.98)):
            px=min(op,c0*k) if lw<=c0*k else c1;b[nm+"_or_close"]=e/px-1;b[nm+"_fill"]=float(lw<=c0*k)
        out.append(b)
z=pd.DataFrame(out).set_index("date")
for a,e in(("2018","2023"),("2023","2027")):
    g=z[(z.index>=a)&(z.index<e)].groupby(level=0).mean();print("STEADY",a);print((g.mean()*100).round(3).to_dict(),{c:round(track._nw_t(g[c]-g["close"],5),2) for c in("open","lim0_or_close","lim1_or_close","lim2_or_close")})
