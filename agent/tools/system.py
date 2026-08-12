import subprocess
import json
import os
import shutil
import ctypes
from pathlib import Path
from agent.config import WORKSPACE_DIR

def get_processes(filter_name: str = '') -> str:
    try:
        if filter_name:
            cmd = f"Get-Process -Name '*{filter_name}*' -ErrorAction SilentlyContinue | Select-Object -First 30 Id, ProcessName, CPU, WorkingSet | ConvertTo-Json"
        else:
            cmd = "Get-Process -ErrorAction SilentlyContinue | Sort-Object -Descending CPU, WorkingSet | Select-Object -First 30 Id, ProcessName, CPU, WorkingSet | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return res.stdout if res.stdout.strip() else "未找到匹配进程。"
    except Exception as e:
        return f"获取进程失败: {str(e)}"

def get_services(filter_name: str = '') -> str:
    try:
        if filter_name:
            cmd = f"Get-Service -Name '*{filter_name}*' -ErrorAction SilentlyContinue | Select-Object -First 30 Name, DisplayName, Status | ConvertTo-Json"
        else:
            cmd = "Get-Service -ErrorAction SilentlyContinue | Select-Object -First 40 Name, DisplayName, Status | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return res.stdout if res.stdout.strip() else "未找到匹配服务。"
    except Exception as e:
        return f"获取服务失败: {str(e)}"

def get_disk_memory() -> str:
    try:
        drives_info = []
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            root = f"{letter}:\\"
            if os.path.exists(root):
                try:
                    total, used, free = shutil.disk_usage(root)
                    drives_info.append({
                        "Drive": f"{letter}:",
                        "TotalGB": round(total / (1024**3), 2),
                        "FreeGB": round(free / (1024**3), 2),
                        "UsedPercent": f"{round((used / total) * 100, 1)}%"
                    })
                except Exception:
                    pass
        
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ('dwLength', ctypes.c_ulong),
                ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong),
                ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong),
                ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong),
                ('ullAvailVirtual', ctypes.c_ulonglong),
                ('sullAvailExtendedVirtual', ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        
        mem_info = {
            "TotalPhysicalGB": round(stat.ullTotalPhys / (1024**3), 2),
            "AvailablePhysicalGB": round(stat.ullAvailPhys / (1024**3), 2),
            "UsedPercent": f"{stat.dwMemoryLoad}%"
        }
        
        return f"--- 磁盘信息 ---\n{json.dumps(drives_info, ensure_ascii=False, indent=2)}\n\n--- 内存信息 ---\n{json.dumps(mem_info, ensure_ascii=False, indent=2)}"
    except Exception as e:
        return f"获取磁盘/内存失败: {str(e)}"

def get_event_errors(hours: int = 24) -> str:
    try:
        cmd = f"Get-WinEvent -FilterHashtable @{{LogName='System','Application'; Level=1,2; StartTime=(Get-Date).AddHours(-{hours})}} -MaxEvents 20 -ErrorAction SilentlyContinue | Select-Object TimeCreated, LogName, ProviderName, Id, Message | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return res.stdout if res.stdout.strip() else "未发现指定时间段内的 Error/Critical 级别错误事件。"
    except Exception as e:
        return f"获取事件日志失败: {str(e)}"

def test_network(target: str = 'www.baidu.com') -> str:
    try:
        cmd = f"Test-Connection -ComputerName {target} -Count 2 -ErrorAction SilentlyContinue | Select-Object Address, IP4Address, ResponseTime | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return res.stdout if res.stdout.strip() else f"Ping {target} 测试失败或超时。"
    except Exception as e:
        return f"网络测试失败: {str(e)}"

def read_file(path: str = '') -> str:
    if not path:
        return "[参数错误] 缺少必要参数 path"
    try:
        p = Path(path)
        if not p.exists():
            return f"文件 {path} 不存在。"
        return p.read_text(encoding='utf-8', errors='ignore')[:4000]
    except Exception as e:
        return f"读取文件失败: {str(e)}"

def write_report(filename: str = '', content: str = '') -> str:
    if not filename or not content:
        return "[参数错误] 缺少必要参数 filename 或 content"
    try:
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        out_path = WORKSPACE_DIR / filename
        out_path.write_text(content, encoding='utf-8')
        return f"诊断报告已写入: {out_path}"
    except Exception as e:
        return f"写入报告失败: {str(e)}"
