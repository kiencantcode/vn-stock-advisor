"""Cho GitHub Actions: lịch dự phòng chỉ chạy lại khi kết quả chưa mới. Chỉ dùng thư viện chuẩn."""
import json
import sys
from datetime import datetime, timedelta, timezone


def is_fresh(site: dict, now: datetime) -> bool:
    """now: giờ Việt Nam (không kèm múi giờ)."""
    close = now.replace(hour=15, minute=20, second=0, microsecond=0)
    if now < close:
        close -= timedelta(days=1)
    while close.weekday() >= 5:
        close -= timedelta(days=1)
    updated = datetime.strptime(site["updated"], "%Y-%m-%d %H:%M")
    if updated < close or site.get("warnings") or (site.get("steady") or {}).get("asof") != site["asof"]:
        return False
    # có phiên mới, hoặc đã thử lại đủ muộn (ngày nghỉ lễ không có phiên)
    return site["asof"] >= close.strftime("%Y-%m-%d") or updated >= close + timedelta(hours=4)


if __name__ == "__main__":
    try:
        with open("output/site.json", encoding="utf-8") as f:
            ok = is_fresh(json.load(f), datetime.now(timezone(timedelta(hours=7))).replace(tzinfo=None))
    except (OSError, ValueError, KeyError):
        ok = False
    print("skip=" + ("true" if ok else "false"))
    sys.exit(0)
