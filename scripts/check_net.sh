#!/usr/bin/env bash
set -u

echo "[+] 网络接口与 IP 配置"
ip addr 2>/dev/null || ifconfig 2>/dev/null || true

echo
echo "[+] 默认路由"
ip route 2>/dev/null || route -n 2>/dev/null || true

echo
echo "[+] DNS 配置"
if command -v resolvectl >/dev/null 2>&1; then
    resolvectl status
else
    cat /etc/resolv.conf 2>/dev/null || true
fi

echo
echo "[+] 代理环境变量"
env | grep -iE '^(http|https|all|no)_proxy=' || echo "未设置代理环境变量"

echo
echo "[+] 外网连通性"
ping -c 2 -W 3 "${1:-www.baidu.com}" 2>&1 || true
