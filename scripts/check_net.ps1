# Windows ????????
Write-Host "[+] ???? IP ? DNS ??..." -ForegroundColor Green
Get-NetIPConfiguration | Select-Object InterfaceAlias, IPv4Address, IPv4DefaultGateway, DNSServer

Write-Host "`n[+] ???? WinHTTP ????..." -ForegroundColor Green
netsh winhttp show proxy

Write-Host "`n[+] ?????" -ForegroundColor Yellow
