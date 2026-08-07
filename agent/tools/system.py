import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from agent.config import WORKSPACE_DIR

def get_processes(filter_name: str = '') -> str:
    try:
        cmd = "Get-Process | Select-Object -First 30 Id, ProcessName, CPU, WorkingSet64 | ConvertTo-Json"
        if filter_name:
            cmd = f"Get-Process -Name '*{filter_name}*' | Select-Object Id, ProcessName, CPU, WorkingSet64 | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return res.stdout if res.stdout else "??????????"
    except Exception as e:
        return f"??????: {str(e)}"

def get_services(filter_name: str = '') -> str:
    try:
        cmd = "Get-Service | Select-Object -First 30 Name, DisplayName, Status, StartType | ConvertTo-Json"
        if filter_name:
            cmd = f"Get-Service -Name '*{filter_name}*' | Select-Object Name, DisplayName, Status, StartType | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return res.stdout if res.stdout else "??????????"
    except Exception as e:
        return f"??????: {str(e)}"

def get_disk_memory() -> str:
    try:
        cmd = "@'\nGet-CimInstance Win32_LogicalDisk | Select-Object DeviceID, VolumeName, @{N='SizeGB';E={[math]::round($_.Size/1GB,2)}}, @{N='FreeGB';E={[math]::round($_.FreeSpace/1GB,2)}}\nGet-CimInstance Win32_OperatingSystem | Select-Object @{N='TotalMemGB';E={[math]::round($_.TotalVisibleMemorySize/1MB,2)}}, @{N='FreeMemGB';E={[math]::round($_.FreePhysicalMemory/1MB,2)}}\n'@ | powershell -NoProfile -"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID, @{N='FreeGB';E={[math]::round($_.FreeSpace/1GB,2)}}, @{N='TotalGB';E={[math]::round($_.Size/1GB,2)}} | ConvertTo-Json"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        res_mem = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_OperatingSystem | Select-Object @{N='FreeMemGB';E={[math]::round($_.FreePhysicalMemory/1MB,2)}}, @{N='TotalMemGB';E={[math]::round($_.TotalVisibleMemorySize/1MB,2)}} | ConvertTo-Json"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return f"??????\n{res.stdout}\n??????\n{res_mem.stdout}"
    except Exception as e:
        return f"????/??????: {str(e)}"

def get_event_errors(hours: int = 24) -> str:
    try:
        cmd = f"Get-WinEvent -FilterHashtable @{{LogName='System','Application'; Level=2; StartTime=(Get-Date).AddHours(-{hours})}} -MaxEvents 15 | Select-Object TimeCreated, LogName, ProviderName, Id, Message | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return res.stdout if res.stdout else "?????????"
    except Exception as e:
        return f"????????: {str(e)}"

def test_network(target: str = 'www.baidu.com') -> str:
    try:
        cmd = f"Test-Connection -ComputerName {target} -Count 2 | Select-Object Address, IP4Address, ResponseTime | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return res.stdout if res.stdout else f"Ping {target} ??????"
    except Exception as e:
        return f"??????: {str(e)}"

def read_file(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return f"?? {path} ???"
        return p.read_text(encoding='utf-8', errors='ignore')[:4000]
    except Exception as e:
        return f"??????: {str(e)}"

def write_report(filename: str, content: str) -> str:
    try:
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        out_path = WORKSPACE_DIR / filename
        out_path.write_text(content, encoding='utf-8')
        return f"????????: {out_path}"
    except Exception as e:
        return f"??????: {str(e)}"
