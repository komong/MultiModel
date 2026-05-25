$src1 = "d:\Desktop\Test\MultiModel\scripts\check_docker.sh"
$dst1 = "\\wsl.localhost\Ubuntu\tmp\check_docker.sh"
Copy-Item $src1 $dst1 -Force
wsl -d Ubuntu -e bash -c "chmod +x /tmp/check_docker.sh && bash /tmp/check_docker.sh"
