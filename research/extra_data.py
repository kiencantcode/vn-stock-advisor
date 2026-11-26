"""V5: tải khối ngoại (từ 2018-08) và P/E, P/B, P/S, vốn hoá theo ngày (từ 2017-12) từ VNDirect.
Chạy từ thư mục gốc: python research/extra_data.py  ->  data/cache/vnd_extra.pkl.gz"""
import sys, os, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
sys.path.insert(0, ".")
from advisor import vnd

OUT = "data/cache/vnd_extra.pkl.gz"
RATIOS = {"51006": "pe", "51012": "pb", "51011": "ps", "51003": "mcap"}


def codes() -> list:
    """Mọi mã HOSE từng nằm trong top 100 thanh khoản (giống research/lab_steady.py)."""
    p = pd.read_pickle("data/cache/vnd_px.pkl.gz")
    W = lambda k: p.pivot(index="date", columns="code", values=k)
    C = W("adClose"); C = C[C.notna().sum(axis=1) > 100]
    VAL, FL = W("nmValue").reindex(C.index), W("floor").reindex(C.index) == "HOSE"
    rk = VAL.rolling(60, min_periods=40).median().where(FL).rank(axis=1, ascending=False).where(C.notna().cumsum() >= 250)
    return sorted(rk.columns[(rk <= 100).any()])


def one(code: str):
    for a in range(3):
        try:
            f = vnd._get("foreigns", q=f"code:{code}", size=5000)
            r = [vnd._get("ratios", q=f"code:{code}~itemCode:{k}", size=5000).assign(item=v) for k, v in RATIOS.items()]
            return code, f, pd.concat(r, ignore_index=True)
        except Exception as e:
            if a == 2:
                print(code, "lỗi", e, flush=True); return code, pd.DataFrame(), pd.DataFrame()
            time.sleep(5)


if __name__ == "__main__":
    cs = codes(); print(len(cs), "mã", flush=True)
    F, R = [], []
    with ThreadPoolExecutor(4) as ex:
        for n, (c, f, r) in enumerate(ex.map(one, cs)):
            if len(f): F.append(f.assign(code=c)[["code", "tradingDate", "buyVal", "sellVal", "netVal", "totalRoom", "currentRoom"]])
            if len(r): R.append(r.assign(code=c)[["code", "reportDate", "item", "value"]])
            if n % 25 == 0: print(n, c, flush=True)
    f = pd.concat(F, ignore_index=True); f["date"] = pd.to_datetime(f.pop("tradingDate"))
    r = pd.concat(R, ignore_index=True); r["date"] = pd.to_datetime(r.pop("reportDate"))
    r = r.pivot_table(index=["date", "code"], columns="item", values="value", aggfunc="last").reset_index()
    pd.to_pickle({"foreign": f.drop_duplicates(["code", "date"]), "ratios": r}, OUT)
    print("xong", len(f), len(r), f.date.min(), r.date.min())
