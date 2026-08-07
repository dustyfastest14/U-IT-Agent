# Windows 深入网络连通性排查脚本
Write-Host "[+] 检查接口 IP 与 DNS 配置..." -ForegroundColor Green
Get-NetIPConfiguration | Select-Object InterfaceAlias, IPv4Address, IPv4DefaultGateway, DNSServer

Write-Host "
[+] 检查 WinHTTP 代理配置..." -ForegroundColor Green
netsh winhttp show proxy

Write-Host "
[+] 网络连通性测试完成。" -ForegroundColor Yellow