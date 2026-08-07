import subprocess
from pathlib import Path
from agent.config import SCRIPTS_DIR, SKILLS_DIR, CONFIRM_MODE, FORBIDDEN_KEYWORDS

def is_cmd_safe(cmd: str) -> bool:
    cmd_lower = cmd.lower()
    for kw in FORBIDDEN_KEYWORDS:
        if kw in cmd_lower:
            return False
    return True

def run_powershell(command: str) -> str:
    if not is_cmd_safe(command):
        return f"[安全拦截] 命令包含禁止的高危操作指令，拒绝执行: {command}"
    
    if CONFIRM_MODE:
        print(f"\n[安全确认] Agent 请求执行 PowerShell 命令:")
        print(f"  >>> {command}")
        choice = input("是否允许执行？ [y/N]: ").strip().lower()
        if choice != 'y':
            return "[用户拒绝] 用户取消了该命令的执行。"
    
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        out = res.stdout if res.stdout else res.stderr
        return out if out else "命令已成功执行（无打印输出）。"
    except Exception as e:
        return f"PowerShell 执行异常: {str(e)}"

def run_script(script_name: str, args: str = '') -> str:
    target_script = None
    
    # 查找 scripts 目录
    script_in_global = SCRIPTS_DIR / script_name
    if script_in_global.exists():
        target_script = script_in_global
    else:
        # 查找 skills 内部 scripts 目录
        for sdir in SKILLS_DIR.glob('*'):
            candidate = sdir / 'scripts' / script_name
            if candidate.exists():
                target_script = candidate
                break
    
    if not target_script:
        return f"[错误] 未能定位诊断脚本: {script_name}"
    
    full_cmd = f"& '{target_script}' {args}"
    if not is_cmd_safe(full_cmd):
        return f"[安全拦截] 脚本调用包含高危指令，拒绝执行。"
    
    if CONFIRM_MODE:
        print(f"\n[安全确认] Agent 请求执行诊断脚本:")
        print(f"  脚本路径: {target_script}")
        print(f"  附加参数: {args}")
        choice = input("是否允许执行该脚本？ [y/N]: ").strip().lower()
        if choice != 'y':
            return "[用户拒绝] 用户取消了脚本的执行。"
    
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(target_script), args], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        out = res.stdout if res.stdout else res.stderr
        return out if out else "脚本成功执行（无返回输出）。"
    except Exception as e:
        return f"脚本执行异常: {str(e)}"