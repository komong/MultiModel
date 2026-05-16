$log = "\\wsl.localhost\Ubuntu\tmp\startup.log"

function Log { param($m) $m | Out-File $log -Append; Write-Host $m }

Log "=== Starting WSL ==="
wsl -d Ubuntu -- bash -c "" 2>&1 | Out-Null
Start-Sleep 2

Copy-Item "d:\Desktop\Test\MultiModel\model-tracing\langfuse-docker-compose.yml" "\\wsl.localhost\Ubuntu\tmp\" -Force
Copy-Item "d:\Desktop\Test\MultiModel\wsl_start.sh" "\\wsl.localhost\Ubuntu\tmp\" -Force

Log "=== Run Setup ==="
$result = wsl -d Ubuntu -e bash -c "chmod +x /tmp/wsl_start.sh && bash /tmp/wsl_start.sh" 2>&1
Log $result

Log "=== Test localhost:3000 ==="
try {
    $r = curl.exe --noproxy '*' -sI --connect-timeout 10 http://localhost:3000
    Log "HTTP Status: $r"
} catch {
    Log "FAILED: $_"
}

Log "=== Test WSL IP ==="
$ip = wsl -d Ubuntu -e bash -c "ip addr show eth0 | grep 'inet ' | awk '{print \$2}'" 2>&1
Log "WSL IP: $ip"

Log "=== Done ==="
Write-Host "`nComplete. Check $log for details"
Read-Host "Press Enter to exit"
