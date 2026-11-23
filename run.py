#!/usr/bin/env python3
"""Cách dùng:
  python run.py                  # cập nhật dữ liệu + xếp hạng + báo cáo
  python run.py --demo           # dữ liệu giả lập (không cần mạng)
  python run.py --sector thep    # chỉ hiển thị một ngành
  python run.py --backtest       # bắt buộc kiểm định lại
  python run.py --score          # chỉ chấm điểm nhật ký, không huấn luyện
  python run.py --accuracy       # đo lại độ chính xác ngắn/trung/dài hạn
  python run.py --watch 30       # lặp lại mỗi 30 phút
"""
import argparse
import sys
import time
import traceback

import pandas as pd

from advisor import pipeline

for s in (sys.stdout, sys.stderr):  # tiếng Việt trên Windows
    if hasattr(s, "reconfigure"):
        s.reconfigure(encoding="utf-8", errors="replace")


def once(args):
    cfg = pipeline.load_config(args.config)
    if args.score:
        print("\n".join(pipeline.score_only(cfg, args.provider)))
        return
    df, info = pipeline.run(cfg, "synthetic" if args.demo else args.provider, args.sector, args.backtest,
                            log=args.config is None, force_accuracy=args.accuracy)
    path = pipeline.write_outputs(df, info, args.sector)
    pd.set_option("display.width", 250)
    if args.demo:
        print("*** DỮ LIỆU GIẢ, chỉ để thử ***")
    print(df.to_string(index=False) if len(df) else "Không có kết quả")
    for n in ("dev", "holdout"):
        m = info["validation"].get(n)
        if m:
            print(f"Kiểm định {n}: IC {m['rank_ic']:.3f} (t={m['ic_t']:.1f}), vượt trội sau phí "
                  f"{m['net_excess_yr']:+.1%}/năm (t={m['net_t']:.1f}), độ phủ {m['coverage80']:.0%}")
    print("Cổng tín hiệu MUA:", "MỞ" if info["validation"]["gate"] else "KHOÁ (chưa chứng minh có lời sau phí)")
    print("\n--- Độ chính xác theo kỳ hạn ---\n" + "\n".join(info["accuracy"]) + "\n" + info["learned"])
    if info["forecast"]:
        print("\n--- Dự báo chuỗi thời gian (output/forecast.html) ---\n" + "\n".join(info["forecast"]))
    if info["live"]:
        print("\n--- Điểm trên dữ liệu sống ---\n" + "\n".join(info["live"]))
    for w in info["warnings"]:
        print("CẢNH BÁO:", w)
    print(f"\nBáo cáo: {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
    ap.add_argument("--config")
    ap.add_argument("--provider", choices=["auto", "vnstock", "entrade", "synthetic"])
    ap.add_argument("--sector")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--backtest", action="store_true")
    ap.add_argument("--accuracy", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--watch", type=int, help="lặp lại mỗi N phút")
    a = ap.parse_args()
    if a.score and a.demo:
        ap.error("--score chỉ dùng với dữ liệu thật")
    if not a.watch:
        once(a)
    while a.watch:
        try:
            once(a)
        except (Exception, SystemExit):
            traceback.print_exc()  # lỗi mạng tạm thời không được làm dừng vòng lặp
        a.backtest = a.accuracy = False
        time.sleep(a.watch * 60)
