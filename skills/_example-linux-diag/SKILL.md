# 技能: Linux 基础系统与网络诊断
name: linux-diag
description: 专门排查 Linux 服务、内核日志、资源和网络连通性问题
platforms: Linux
triggers: 服务不可用, 容器异常, OOM, 内核错误, 网络不通, DNS异常

## 标准排查步骤
1. 使用 `get_services` 查看 systemd 服务状态；没有 systemd 时查看 service 状态。
2. 使用 `get_event_errors`、`get_crash_records` 检查 journalctl、OOM、Panic 和 /var/crash。
3. 使用 `get_disk_memory`、`get_processes` 评估磁盘、内存、CPU 压力。
4. 使用 `test_network` 或 `run_script(check_net.sh)` 排查 DNS、路由和外网连通性。

## 注意事项
日志读取可能需要 root 权限。停止服务、修改网络、安装软件或修改权限必须先获得用户确认。
