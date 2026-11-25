import sys; sys.path[:0]=["research","."]
import numpy as np, pandas as pd, pickle, lab_all as A, lab_steady as L
src=open("research/evaluate.py",encoding="utf8").read();exec(src[:src.index("def report")])
Z=pickle.load(open("research/all.pkl","rb"));V=pickle.load(open("research/steady.pkl","rb"));E=V["etf"]
key=("lgb20",20,100,5,6,"lim","none");print("overlap 1d",Z["ov"][("lgb20",20,100,6)]);S=L.mat("lgb20",20);print("overlap 5d",L.overlap(S,100,6,5))
O={i:list(map(int,L.order(S,i,100))) for i in range(L.i0,L.n)}
def line(r):
    s=pd.Series(r,L.G[L.i0:]);o={}
    for n,a,b in(("18-22","2018","2023"),("23-26","2023","2027")):
        z=s[(s.index>=a)&(s.index<b)];q=st(z);o.update({n:q["CAGR"],"dd "+n:q["maxDD"],"t_fund "+n:t(z,E[(E.index>=a)&(E.index<b)])})
    return o
rows={"base":line(A.sim(O,6,5,"lim",(0,0,0))),"live match":line(Z["R"][key].values)}
for c in(.006,.008,.01):rows[f"cost {c:.1%}"]=line(A.sim(O,6,5,"lim",(0,0,0),cost=c))
rows["buy at close"]=line(A.sim(O,6,5,"close",(0,0,0)));rows["trailing 10%"]=line(A.sim(O,6,5,"lim",(0,0,.1)));rows["V3"]=line(Z["R"][("lgb20",20,100,20,10,"close","none")].values);rows["10 stocks"]=line(A.sim(O,10,5,"lim",(0,0,0)))
O50={i:list(map(int,L.order(S,i,50))) for i in range(L.i0,L.n)};rows["top 50 only"]=line(A.sim(O50,6,5,"lim",(0,0,0)))
lo=A.LO.copy();A.LO=lo*1.003;rows["limit must trade through 0.3%"]=line(A.sim(O,6,5,"lim",(0,0,0)));A.LO=lo
i0=L.i0
for d in range(1,5):
    L.i0=i0+d;r=A.sim(O,6,5,"lim",(0,0,0));s=pd.Series(r,L.G[L.i0:]);L.i0=i0
    o={}
    for n,a,b in(("18-22","2018","2023"),("23-26","2023","2027")):
        z=s[(s.index>=a)&(s.index<b)];q=st(z);o.update({n:q["CAGR"],"dd "+n:q["maxDD"],"t_fund "+n:t(z,E[(E.index>=a)&(E.index<b)])})
    rows[f"start +{d}"]=o
print(pd.DataFrame(rows).T.round(2).to_string())
s=pd.Series(A.sim(O,6,5,"lim",(0,0,0)),L.G[L.i0:]);print(((1+pd.DataFrame({"m":s,"E":E})).groupby(s.index.year).prod()-1).round(2).T.to_string())
# each start day on its own
_orig=A.sim
for d in range(5):
    L.i0=i0+d
    out=None
    import types
    src_=open("research/lab_all.py",encoding="utf8").read().replace("range(0, STEP, STEP // 5)","[0]");ns={"__name__":"x"};exec(compile(src_,"x","exec"),ns);r=ns["sim"](O,6,5,"lim",(0,0,0));s=pd.Series(r,L.G[L.i0:]);L.i0=i0
    print("start",d,[round(st(s[(s.index>=a)&(s.index<b)])["CAGR"],3) for a,b in(("2018","2023"),("2023","2027"))])
