import subprocess
import json
from pathlib import Path
from agent.config import WORKSPACE_DIR

def get_processes(filter_name: str = '') -> str:
    try:
        cmd = "Get-Process | Select-Object Id, ProcessName, CPU, WorkingSet | ConvertTo-Json"
        if filter_name:
            cmd = f"Get-Process -Name '*{filter_name}*' | Select-Object Id, ProcessName, CPU, WorkingSet | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return res.stdout if res.stdout else "未找到匹配进程。"
    except Exception as e:
        return f"获取进程失败: {str(e)}"

def get_services(filter_name: str = '') -> str:
    try:
        cmd = "Get-Service | Select-Object Name, DisplayName, Status | ConvertTo-Json"
        if filter_name:
            cmd = f"Get-Service -Name '*{filter_name}*' | Select-Object Name, DisplayName, Status | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return res.stdout if res.stdout else "未找到匹配服务。"
    except Exception as e:
        return f"获取服务失败: {str(e)}"

def get_disk_memory() -> str:
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID, @{N='FreeGB';E={[math]::round(.FreeSpace/1GB,2)}}, @{N='TotalGB';E={[math]::round(.Size/1GB,2)}} | ConvertTo-Json"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        res_mem = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_OperatingSystem | Select-Object @{N='FreeMemGB';E={[math]::round(.FreePhysicalMemory/1MB,2)}}, @{N='TotalMemGB';E={[math]::round(.TotalVisibleMemorySize/1MB,2)}} | ConvertTo-Json"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return f"--- 磁盘信息 ---\n{res.stdout}\n--- 内存信息 ---\n{res_mem.stdout}"
    except Exception as e:
        return f"获取磁盘/内存失败: {str(e)}"

def get_event_errors(hours: int = 24) -> str:
    try:
        cmd = f"Get-WinEvent -FilterHashtable @{{LogName='System','Application'; Level=2; StartTime=(Get-Date).AddHours(-{hours})}} -MaxEvents 15 | Select-Object TimeCreated, LogName, ProviderName, Id, Message | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return res.stdout if res.stdout else "未发现最近错误事件。"
    except Exception as e:
        return f"获取事件日志失败: {str(e)}"

def test_network(target: str = 'www.baidu.com') -> str:
    try:
        cmd = f"Test-Connection -ComputerName {target} -Count 2 | Select-Object Address, IP4Address, ResponseTime | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return res.stdout if res.stdout else f"Ping {target} 测试失败或超时。"
    except Exception as e:
        return f"网络测试失败: {str(e)}"

def read_file(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return f"文件 {path} 不存在。"
        return p.read_text(encoding='utf-8', errors='ignore')[:4000]
    except Exception as e:
        return f"读取文件失败: {str(e)}"

def write_report(filename: str, content: str) -> str:
    try:
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        out_path = WORKSPACE_DIR / filename
        out_path.write_text(content, encoding='utf-8')
        return f"诊断报告已写入: {out_path}"
    except Exception as e:
        return f"写入报告失败: {str(e)}"