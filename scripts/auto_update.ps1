# Dự phòng cho GitHub Actions: chạy bởi Task Scheduler mỗi tối trên máy nhà.
# Nếu trang đã có phiên mới (GitHub đã chạy) thì bỏ qua; nếu chưa thì tự cập nhật và đẩy lên (trang tự xuất bản lại).
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$log = Join-Path $root "data\cache\auto_update.log"
function Write-Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File -FilePath $log -Append -Encoding utf8 }
$py = Join-Path $root ".venv\Scripts\python.exe"

git pull --ff-only -q 2>&1 | Out-Null
$fresh = & $py advisor/fresh.py
if ($fresh -match "skip=true") { Write-Log "Đã mới, bỏ qua"; exit 0 }

Write-Log "Bắt đầu cập nhật"
& $py run.py *>> $log
if ($LASTEXITCODE -ne 0) { Write-Log "run.py lỗi ($LASTEXITCODE)"; exit 1 }
git add output 2>&1 | Out-Null
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Write-Log "Không có gì mới"; exit 0 }
git commit -q -m "Cập nhật dự báo $(Get-Date -Format 'yyyy-MM-dd') (máy nhà)" 2>&1 | Out-Null
git pull --rebase -q 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    # GitHub vừa cập nhật cùng lúc: bỏ bản của máy, giữ bản trên GitHub
    git rebase --abort 2>&1 | Out-Null
    git reset --keep origin/main 2>&1 | Out-Null
    Write-Log "Trùng với GitHub, giữ bản GitHub"; exit 0
}
git push -q 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Log "Đã đẩy lên" } else { Write-Log "Đẩy lên lỗi" }
