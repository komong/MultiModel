$src1 = "d:\Desktop\Test\MultiModel\wsl_start.sh"
$dst1 = "\\wsl.localhost\Ubuntu\tmp\wsl_start.sh"
Copy-Item $src1 $dst1 -Force
wsl -d Ubuntu -e bash -c "chmod +x /tmp/wsl_start.sh && bash /tmp/wsl_start.sh"
