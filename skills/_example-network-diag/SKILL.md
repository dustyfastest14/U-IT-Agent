# 技能: Windows 网络故障与 DNS 排查 Skill
name: network-diag
description: 专门排查网卡配置、DNS 异常、Ping 不通、代理故障等网络连通性问题
triggers: 无法上网, 断网, Ping不通, DNS异常, 代理故障

## 标准排查步骤
1. 检查本机网卡与 IP 配置 (ipconfig /all)
2. 测试外网节点连通性 (	est_network)
3. 检查系统 WinHTTP 代理配置
4. 执行 check_net.ps1 深入排查 DNS 与 Proxy

## 注意事项
排查过程中避免修改网卡物理 IP 地址；修改 DNS 或代理前须获得用户确认。