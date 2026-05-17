# WSL2 端口转发自动更新脚本
# 每次开机自动获取 WSL2 最新 IP，并更新端口转发规则
# 让你可以一直用 localhost:3000 和 localhost:4000 访问 WSL 里的服务

# 需要管理员权限运行
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "请用管理员身份运行此脚本！" -ForegroundColor Red
    exit 1
}

# 获取 WSL2 的当前 IP
$wslIP = (wsl hostname -I).Trim().Split(" ")[0]

if (-not $wslIP) {
    Write-Host "无法获取 WSL2 的 IP，请确认 WSL 已启动。" -ForegroundColor Red
    exit 1
}

Write-Host "WSL2 当前 IP：$wslIP" -ForegroundColor Cyan

# 要转发的端口列表（可以按需添加）
$ports = @(3000, 4000)

foreach ($port in $ports) {
    # 先删除旧规则（忽略报错）
    netsh interface portproxy delete v4tov4 listenport=$port listenaddress=127.0.0.1 2>$null

    # 添加新规则
    netsh interface portproxy add v4tov4 `
        listenport=$port `
        listenaddress=127.0.0.1 `
        connectport=$port `
        connectaddress=$wslIP

    Write-Host "已设置：localhost:$port → $wslIP`:$port" -ForegroundColor Green
}

Write-Host ""
Write-Host "完成！现在可以用 localhost:3000 和 localhost:4000 访问服务了。" -ForegroundColor Green
