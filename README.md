# VN Stock Advisor

Lấy dữ liệu -> đặc trưng -> xếp hạng cổ phiếu -> khoảng giá -> báo cáo HTML/CSV/JSON.
Kết quả kiểm định và giới hạn: xem [REPORT.md](REPORT.md).

## Cài đặt (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Chạy
```powershell
python run.py                # dữ liệu thật -> output/report.html
python run.py --demo         # dữ liệu GIẢ -> output/demo/report.html
python run.py --sector thep  # hiển thị một ngành -> output/report_thep.html
python run.py --backtest     # kiểm định lại ngay
python run.py --watch 30     # tự cập nhật mỗi 30 phút
```
Lần đầu mất vài phút (tải ~13 năm dữ liệu và kiểm định); các lần sau khoảng 1,5 phút.
Tự kiểm định lại sau 30 ngày hoặc khi đổi cấu hình/mô hình.

## Tín hiệu
- `MUA`: hạng top 20% **và** kiểm định sau phí đạt ý nghĩa thống kê.
- `HANG CAO`: top 20% nhưng kiểm định chưa đạt, chỉ tham khảo.
- `TRUNG LAP` / `HANG THAP`: giữa / 20% cuối.
- `RUI RO CAO`: từ 3 phiên giảm trên 6% trong 20 phiên.

## Trang web (GitHub Pages)
Workflow `.github/workflows/daily.yml` chạy 16:30 giờ VN thứ 2 - thứ 6 (GitHub có thể chạy trễ), commit `output/` và xuất bản trang.
Trên trang, bấm **Update now** để cập nhật; chủ repo có thể thêm khoá trong **Button settings** để chỉ cần một lần bấm.
Cài lần đầu: Settings > Pages > Source: **GitHub Actions**. Khi đã chạy trên GitHub thì KHÔNG bật tác vụ tự chạy trên máy;
trước khi chạy trên máy hãy `git pull`, để hai nhật ký không xung đột.

Không phải lời khuyên đầu tư. Giá là nghìn đồng.

## Nhật ký và chấm điểm trên dữ liệu sống
Mỗi lần `python run.py` (dữ liệu thật, cấu hình mặc định) tự ghi xếp hạng vào `output/history/rankings.csv`, mỗi phiên một lần,
không ghi đè. Chỉ những bản ghi **trước 9:00 phiên kế tiếp** mới được chấm. Cần horizon + 1 phiên (6 với mặc định) để chấm xong.
```powershell
python run.py --score        # chấm điểm ngay, không huấn luyện
```
- `output/history/scores.csv`: điểm từng phiên. Báo cáo HTML có mục "Điểm trên dữ liệu sống".
- Đừng sửa `rankings.csv`; mở bằng Excel thì đóng lại trước 16:30.
- Đổi `features.py`, `model.py`, `horizon` hoặc danh sách mã trong `sectors` sẽ bắt đầu chấm lại từ đầu.
- Dưới 60 phiên: chưa kết luận. Điểm sống không tự mở khoá tín hiệu `MUA`.

Tự chạy 16:30 thứ 2 - thứ 6 (PowerShell; chạy bù nếu máy tắt lúc đó):
```powershell
$a = New-ScheduledTaskAction -Execute "E:\vn-stock-advisor\daily.bat"
$t = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 16:30
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "VN Stock Advisor" -Action $a -Trigger $t -Settings $s
```
Nhật ký chạy: `output/history/daily.log`. Gỡ: `Unregister-ScheduledTask -TaskName "VN Stock Advisor"`.

## Kỳ hạn và độ chính xác
Mô hình là **ngắn hạn: 5 phiên (~1 tuần)**. Báo cáo có mục "Độ chính xác theo kỳ hạn" (đo lại mỗi 30 ngày, khoảng 5-8 phút).
```powershell
python run.py --accuracy     # đo lại ngay
```

## Học từ dữ liệu sống
- Mỗi lần chạy, mô hình huấn luyện lại với mọi kết quả thật đã biết (trễ 5 phiên vì phải chờ kết quả).
- Khoảng giá tự hiệu chỉnh theo ~1 năm gần nhất.
- Nhật ký ghi thêm hạng của bản "đóng băng" (không học dữ liệu mới) để đo việc học có ích không.
- Sau 60 phiên, nếu điểm sống âm có ý nghĩa thống kê thì tín hiệu hạng cao chuyển thành `TAM DUNG`.

## Dự báo chuỗi thời gian
Mỗi lần `python run.py` tạo `output/forecast.html`: biểu đồ và dải giá phiên +1..+5 cho từng mã, học lại từ giá đóng cửa mới nhất.
- Chạy sau 15:00: dùng giá hôm nay. Chạy trước 15:00: dùng giá đóng cửa phiên trước (không dự báo trong phiên).
- Dải giá: biến động HAR + hiệu chỉnh conformal. Đường giữa: "giá không đổi", trừ khi Holt/Ridge/LightGBM thắng có ý nghĩa
  thống kê (t >= 2.4) trên 500 phiên gần nhất.
- Ghi vào `output/history/forecasts.csv` (không ghi đè); `python run.py --score` chấm bằng giá thật.
- Mỗi lần chạy khoảng 1,5 phút.

## Danh sách ổn định (giữ từ 1 tuần trở lên, trên giấy)

- Trang web, mục **Steady picks**; mã nguồn `advisor/steady.py`, dữ liệu `advisor/vnd.py`. Xem lại mỗi 5 phiên, giữ 6 mã. Kết quả và giới hạn: `STEADY_REPORT.md`.
- Nhật ký chỉ ghi thêm: `output/history/steady_rankings.csv`. Học lại vào 1/1 và 1/7.
- Lần chạy đầu tải toàn bộ lịch sử từ VNDirect (2-3 phút).
