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
    """获取系统崩溃转储记录、蓝屏Dump、内核Panic或OOM记录"""
    if IS_WINDOWS:
        cmd = r'''
        $dumps = Get-ChildItem -Path "C:\Windows\Minidump" -ErrorAction SilentlyContinue | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize | Out-String;
        $events = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName=@('Microsoft-Windows-WER-SystemErrorReporting','BugCheck')} -MaxEvents %d -ErrorAction SilentlyContinue | Select-Object TimeCreated, Id, Message | Format-List | Out-String;
        "=== MINIDUMP FILES ===`n" + $dumps + "`n=== CRASH EVENTS ===`n" + $events
        ''' % limit
    else:
        cmd = '''
        echo '=== DMESG CRASH / OOM / PANIC ==='
        dmesg -T 2>/dev/null | grep -Ei 'oom|killed process|kernel panic|segfault|error|fatal' | tail -n %d
        echo ''
        echo '=== /var/crash DIRECTORY ==='
        ls -la /var/crash 2>/dev/null
        echo ''
        echo '=== JOURNALCTL RECENT ERRORS ==='
        journalctl -p 3 -xb -n %d --no-pager 2>/dev/null
        ''' % (limit, limit)
    return _run_cmd(cmd)

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
    """安全读取指定文本/e日志文件内容（支持限制行数）"""
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
