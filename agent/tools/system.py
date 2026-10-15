import os
import platform
import subprocess
import datetime
from pathlib import Path
from agent.config import WORKSPACE_DIR, LOGS_DIR, MEMORY_DIR

IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'

def _run_cmd(cmd: str, timeout: int = 30) -> str:
    try:
        if IS_WINDOWS:
            full_cmd = ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', cmd]
        else:
            full_cmd = ['bash', '-c', cmd]
        
        proc = subprocess.run(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        out = proc.stdout.decode('utf-8', errors='ignore').strip()
        if not out and proc.stderr:
            err = proc.stderr.decode('utf-8', errors='ignore').strip()
            if err:
                return f"[Stderr]: {err}"
        return out if out else "(No output)"
    except subprocess.TimeoutExpired:
        return f"[Error]: Command timed out after {timeout} seconds."
    except Exception as e:
        return f"[Error]: {str(e)}"

def get_bsod_crashes(limit: int = 10) -> str:
    """专精蓝屏、异常关机与崩溃转储分析（提取 Windows Minidump、Kernel-Power 41 异常关机及 BugCheck 停机码，或 Linux 内核 Panic/OOM 记录）"""
    if IS_WINDOWS:
        cmd = r'''
        $out = [System.Collections.Generic.List[string]]::new()
        $out.Add("=== 1. MINIDUMP 崩溃转储文件 ===")
        $dumps = Get-ChildItem -Path "C:\Windows\Minidump" -Filter "*.dmp" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First %d Name, Length, LastWriteTime
        if ($dumps) {
            $out.Add(($dumps | Format-Table -AutoSize | Out-String).Trim())
        } else {
            $out.Add("未发现 Minidump 崩溃转储文件（C:\Windows\Minidump 目录为空或未生成）。")
        }
        if (Test-Path "C:\Windows\MEMORY.DMP") {
            $f = Get-Item "C:\Windows\MEMORY.DMP"
            $out.Add("发现完整内存转储: C:\Windows\MEMORY.DMP (大小: $([math]::Round($f.Length/1MB, 2)) MB, 写入时间: $($f.LastWriteTime))")
        }

        $out.Add("`n=== 2. KERNEL-POWER 异常断电与 BUGCHECK 停机事件 ===")
        $known_codes = @{
            0x00000000 = "意外断电/长按电源键强制关机/瞬时掉电"
            0x0000000A = "IRQL_NOT_LESS_OR_EQUAL (驱动程序访问无效内存地址或中断级别过高)"
            0x0000001E = "KMODE_EXCEPTION_NOT_HANDLED (内核模式程序抛出未捕获异常)"
            0x0000003B = "SYSTEM_SERVICE_EXCEPTION (系统服务或驱动执行异常，常见于显卡/网卡驱动)"
            0x00000050 = "PAGE_FAULT_IN_NONPAGED_AREA (非分页内存区域分页错误，硬件内存损坏或驱动异常)"
            0x0000007E = "SYSTEM_THREAD_EXCEPTION_NOT_HANDLED (系统线程异常，常见于系统文件损坏或旧驱动)"
            0x0000009F = "DRIVER_POWER_STATE_FAILURE (电源状态转换超时，常见于休眠/唤醒/驱动挂起)"
            0x000000D1 = "DRIVER_IRQL_NOT_LESS_OR_EQUAL (驱动引用分页内存失败，多为网卡、声卡或外设驱动)"
            0x00000116 = "VIDEO_TDR_FAILURE (显卡驱动无响应并尝试重置失败)"
            0x00000124 = "WHEA_UNCORRECTABLE_ERROR (致命硬件错误，CPU、主板供电或总线故障)"
            0x00000133 = "DPC_WATCHDOG_VIOLATION (DPC 看门狗超时，SSD 固件过旧或关键驱动阻塞系统)"
            0x00000139 = "KERNEL_SECURITY_CHECK_FAILURE (内核安全检查失败，驱动破坏了内核数据结构)"
            0x000000EF = "CRITICAL_PROCESS_DIED (关键系统服务进程意外终止)"
            0x0000001A = "MEMORY_MANAGEMENT (内存管理严重错误，物理内存条接触不良或损坏)"
            0x0000007B = "INACCESSIBLE_BOOT_DEVICE (系统盘无法访问，SATA/NVMe 驱动或分区损坏)"
        }

        $events = Get-WinEvent -FilterHashtable @{LogName='System'; Id=@(41, 1001)} -MaxEvents %d -ErrorAction SilentlyContinue
        if ($events) {
            foreach ($e in $events) {
                $msg = $e.Message.Trim().Split("`n")[0]
                $code_desc = ""
                if ($e.Id -eq 41 -and $e.Properties.Count -gt 0) {
                    $bc = [int64]$e.Properties[0].Value
                    $hex = "0x{0:X8}" -f $bc
                    $meaning = if ($known_codes.ContainsKey($bc)) { $known_codes[$bc] } else { "未知停机码" }
                    $code_desc = " [BugcheckCode: $hex -> $meaning]"
                }
                $out.Add("[$($e.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss'))] EventID: $($e.Id) ($($e.ProviderName))$code_desc`n  $msg")
            }
        } else {
            $out.Add("系统日志中最近未检索到 Kernel-Power 41 或 BugCheck 1001 事件。")
        }
        $out -join "`n"
        ''' % (limit, limit)
    else:
        cmd = '''
        echo '=== 1. LINUX KERNEL PANIC & OOM KILLER LOGS ==='
        dmesg -T 2>/dev/null | grep -Ei 'kernel panic|out of memory|killed process|segfault|machine check exception' | tail -n %d
        echo ''
        echo '=== 2. /var/crash & CORE DUMP DIRECTORY ==='
        ls -lh /var/crash /var/log/dump 2>/dev/null || echo '无崩溃转储文件'
        echo ''
        echo '=== 3. SYSTEMD COREDUMP & JOURNALCTL ERRORS ==='
        if command -v coredumpctl >/dev/null 2>&1; then
            coredumpctl list -n %d 2>/dev/null
        else
            journalctl -p 0..3 -xb -n %d --no-pager 2>/dev/null
        fi
        ''' % (limit, limit, limit)
    return _run_cmd(cmd)

def get_bitlocker_status() -> str:
    """获取所有磁盘分区的 BitLocker 加密状态、保护状态与转换进度（Windows 免提权 CIM 接口，Linux 检查 LUKS 卷）"""
    if IS_WINDOWS:
        cmd = r'''
        $out = [System.Collections.Generic.List[string]]::new()
        $out.Add("=== BITLOCKER / DISK ENCRYPTION STATUS ===")
        try {
            $vols = Get-CimInstance -Namespace root\CIMV2\Security\MicrosoftVolumeEncryption -ClassName Win32_EncryptableVolume -ErrorAction Stop
            foreach ($v in $vols) {
                $drive = if ($v.DriveLetter) { $v.DriveLetter } else { "(无盘符卷 ID: " + $v.DeviceID.Substring(0, [math]::Min(20, $v.DeviceID.Length)) + ")" }
                $prot = switch ($v.ProtectionStatus) {
                    0 { "未启用保护 (Protection Off / 解锁)" }
                    1 { "已启用保护 (Protection On / 加密中或已加密)" }
                    default { "未知状态 ($($v.ProtectionStatus))" }
                }
                $conv = switch ($v.ConversionStatus) {
                    0 { "完全解密 (Fully Decrypted)" }
                    1 { "完全加密 (Fully Encrypted)" }
                    2 { "正在加密进行中" }
                    3 { "正在解密进行中" }
                    4 { "加密已暂停" }
                    5 { "解密已暂停" }
                    default { "状态码 $($v.ConversionStatus)" }
                }
                $method = switch ($v.EncryptionMethod) {
                    0 { "无 (None)" }
                    1 { "AES-128 With Diffuser" }
                    2 { "AES-256 With Diffuser" }
                    3 { "AES-128" }
                    4 { "AES-256" }
                    6 { "XTS-AES-128" }
                    7 { "XTS-AES-256" }
                    default { "方法码 $($v.EncryptionMethod)" }
                }
                $out.Add("卷 [$drive] | 保护状态: $prot | 转换进度: $conv | 加密算法: $method")
            }
        } catch {
            $out.Add("WMI 驱动加密接口查询失败: $($_.Exception.Message)")
        }
        $out -join "`n"
        '''
    else:
        cmd = '''
        echo '=== BLOCK DEVICE ENCRYPTION (LUKS) STATUS ==='
        lsblk -o NAME,FSTYPE,FSVER,LABEL,MOUNTPOINT,SIZE -f 2>/dev/null
        echo ''
        echo '=== DM-CRYPT MAPPINGS ==='
        dmsetup status --target crypt 2>/dev/null || echo '未检测到活动的 LUKS/dm-crypt 加密映射'
        '''
    return _run_cmd(cmd)

def get_processes(limit: int = 25) -> str:
    """获取当前系统活跃进程列表（按CPU占用降序）"""
    if IS_WINDOWS:
        cmd = 'Get-Process | Sort-Object CPU -Descending | Select-Object -First %d Id, ProcessName, CPU, WorkingSet64, Responding | Format-Table -AutoSize | Out-String -Width 4096' % limit
    else:
        cmd = 'ps -eo pid,ppid,user,%cpu,%mem,stat,comm --sort=-%cpu 2>/dev/null | head -n %d' % (limit + 1)
    return _run_cmd(cmd)

def get_services(limit: int = 30) -> str:
    """获取系统关键服务状态"""
    if IS_WINDOWS:
        cmd = 'Get-Service | Where-Object {$_.Status -eq "Running" -or $_.StartType -eq "Automatic"} | Select-Object -First %d Name, DisplayName, Status, StartType | Format-Table -AutoSize | Out-String -Width 4096' % limit
    else:
        cmd = 'systemctl list-units --type=service --state=running,failed --no-pager --no-legend 2>/dev/null | head -n %d' % limit
        res = _run_cmd(cmd)
        if '(No output)' in res or '[Error]' in res:
            cmd = 'service --status-all 2>&1 | head -n %d' % limit
            return _run_cmd(cmd)
        return res
    return _run_cmd(cmd)

def get_disk_memory() -> str:
    """获取磁盘挂载与内存利用率信息"""
    if IS_WINDOWS:
        cmd = r'''
        $disks = Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N="UsedGB";E={[math]::Round($_.Used/1GB, 2)}}, @{N="FreeGB";E={[math]::Round($_.Free/1GB, 2)}}, @{N="TotalGB";E={[math]::Round(($_.Used+$_.Free)/1GB, 2)}} | Format-Table -AutoSize | Out-String;
        $os = Get-CimInstance Win32_OperatingSystem;
        $mem = [PSCustomObject]@{
            TotalRAM_GB = [math]::Round($os.TotalVisibleMemorySize/1MB, 2);
            FreeRAM_GB = [math]::Round($os.FreePhysicalMemory/1MB, 2);
            UsedRAM_GB = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB, 2);
            UsagePercent = [math]::Round((($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/$os.TotalVisibleMemorySize)*100, 2)
        } | Format-Table -AutoSize | Out-String;
        "=== DISK USAGE ===`n" + $disks + "`n=== MEMORY USAGE ===`n" + $mem
        '''
    else:
        cmd = "echo '=== DISK USAGE ==='; df -h; echo ''; echo '=== MEMORY USAGE ==='; free -h"
    return _run_cmd(cmd)

def get_crash_records(limit: int = 20) -> str:
    """获取系统崩溃转储记录、蓝屏Dump、内核Panic或OOM记录（兼容性包装）"""
    return get_bsod_crashes(limit=limit)

def get_event_errors(hours: int = 24, max_events: int = 30) -> str:
    """获取最近指定时间内的系统严重错误与警告日志"""
    if IS_WINDOWS:
        cmd = '''
        $cutoff = (Get-Date).AddHours(-%d);
        Get-WinEvent -FilterHashtable @{LogName=@('System','Application'); Level=@(1,2); StartTime=$cutoff} -MaxEvents %d -ErrorAction SilentlyContinue |
            Select-Object TimeCreated, Id, ProviderName, LevelDisplayName, Message | Format-List | Out-String -Width 4096
        ''' % (hours, max_events)
    else:
        cmd = 'journalctl -p 3 --since "%d hours ago" -n %d --no-pager 2>/dev/null' % (hours, max_events)
    return _run_cmd(cmd)

def test_network(target: str = "www.baidu.com") -> str:
    """测试网络连通性、延迟与DNS解析"""
    target = target.strip().split(';')[0].split('&')[0].split('|')[0]
    if IS_WINDOWS:
        cmd = '''
        $dns = Resolve-DnsName -Name "%s" -ErrorAction SilentlyContinue | Select-Object Name, IPAddress | Format-Table -AutoSize | Out-String;
        $ping = Test-Connection -ComputerName "%s" -Count 4 -ErrorAction SilentlyContinue | Select-Object Address, ResponseTime, Status | Format-Table -AutoSize | Out-String;
        "=== DNS RESOLUTION ===`n" + $dns + "`n=== PING RESULT ===`n" + $ping
        ''' % (target, target)
    else:
        cmd = '''
        echo '=== PING TEST ==='
        ping -c 4 -W 3 "%s" 2>&1
        echo ''
        echo '=== HTTP CONNECTIVITY ==='
        curl -Is --connect-timeout 5 "%s" 2>&1 | head -n 5
        ''' % (target, target)
    return _run_cmd(cmd)

def read_file(file_path: str, max_lines: int = 100) -> str:
    """安全读取指定文本/日志文件内容（支持限制行数）"""
    try:
        p = Path(file_path).resolve()
        if not p.exists():
            return f"[Error]: File not found: {file_path}"
        if not p.is_file():
            return f"[Error]: Path is not a file: {file_path}"
        
        lines = []
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"... (truncated, total displayed {max_lines} lines)")
                    break
                lines.append(line.rstrip('\r\n'))
        return "\n".join(lines)
    except Exception as e:
        return f"[Error]: Failed to read file: {str(e)}"

def write_report(title: str, content: str, format: str = "markdown") -> str:
    """生成结构化运维诊断与修复报告并保存至工作区"""
    try:
        safe_title = "".join(c for c in title if c.isalnum() or c in ('-', '_', ' ')).strip().replace(' ', '_')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.md"
        filepath = WORKSPACE_DIR / filename
        
        full_content = f"# {title}\n\n- **Generated At**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n- **Platform**: {platform.system()} ({platform.release()})\n\n---\n\n{content}\n"
        
        filepath.write_text(full_content, encoding='utf-8')
        return f"Report successfully written to: {str(filepath)}"
    except Exception as e:
        return f"[Error]: Failed to write report: {str(e)}"

def get_machine_history() -> str:
    """读取当前机器的历史画像与过往运维事件记录"""
    try:
        hostname = platform.node()
        machine_file = MEMORY_DIR / 'machines' / f"{hostname}.json"
        
        info = []
        if machine_file.exists():
            info.append(f"=== MACHINE PROFILE ({hostname}) ===")
            info.append(machine_file.read_text(encoding='utf-8', errors='ignore'))
        else:
            info.append(f"No previous machine profile found for {hostname}.")
            
        episodes_dir = MEMORY_DIR / 'episodes'
        if episodes_dir.exists():
            ep_files = sorted([f for f in episodes_dir.glob(f"{hostname}_*.json")], key=lambda x: x.stat().st_mtime, reverse=True)
            if ep_files:
                info.append(f"\n=== RECENT EPISODES ({len(ep_files)} found) ===")
                for ep in ep_files[:3]:
                    info.append(f"--- {ep.name} ---\n" + ep.read_text(encoding='utf-8', errors='ignore'))
        return "\n".join(info)
    except Exception as e:
        return f"[Error]: Failed to retrieve machine history: {str(e)}"
