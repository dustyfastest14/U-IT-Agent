import platform
import re
import shlex
import subprocess
from pathlib import Path

from agent.config import CONFIRM_MODE, FORBIDDEN_KEYWORDS, SCRIPTS_DIR, SKILLS_DIR

IS_WINDOWS = platform.system() == "Windows"
MODIFY_PATTERNS = [
    r"\b(set|remove|stop|restart|new|enable|disable|start|rename|move|copy|add|install|uninstall|update|invoke)-",
    r"\b(kill|taskkill|del|rm|rmdir|mkdir|touch|chmod|chown|chgrp|useradd|userdel|usermod|groupadd|groupdel)\b",
    r"\b(apt|apt-get|yum|dnf|zypper|pacman)\s+(install|remove|purge|update|upgrade)",
    r"\b(systemctl|service)\s+(start|stop|restart|enable|disable|mask|unmask)",
    r"\b(reg\s+(add|delete)|netsh\s+.*(set|add|delete)|sc(\.exe)?\s+(stop|start|config|delete|create))",
    r">>",
    r"(?<!\d)>(?![>&])",
]


def is_cmd_safe(command: str) -> bool:
    """判断命令是否包含配置中明确禁止的高危操作。"""
    command_lower = command.lower()
    return not any(keyword in command_lower for keyword in FORBIDDEN_KEYWORDS)


def is_query_only_cmd(command: str) -> bool:
    """修改系统状态的命令必须经人工确认。"""
    command_lower = command.lower()
    return not any(re.search(pattern, command_lower) for pattern in MODIFY_PATTERNS)


def _confirm(command: str) -> str | None:
    if not CONFIRM_MODE or is_query_only_cmd(command):
        return None

    print("\n[安全确认] Agent 请求执行可能修改系统的命令:")
    print(f"  >>> {command}")
    if input("是否允许执行？ [y/N]: ").strip().lower() != "y":
        return "[用户拒绝] 用户取消了该命令的执行。"
    return None


def run_command(command: str = "", timeout: int = 60) -> str:
    """按当前操作系统执行 PowerShell 或 Bash 命令。"""
    if not command.strip():
        return "[参数错误] run_command 缺少必要参数 command。"
    if not is_cmd_safe(command):
        return "[安全拦截] 命令包含禁止的高危操作指令，拒绝执行。"

    rejected = _confirm(command)
    if rejected:
        return rejected

    executable = "powershell" if IS_WINDOWS else "bash"
    arguments = [executable, "-NoProfile", "-Command", command] if IS_WINDOWS else [executable, "-c", command]
    try:
        result = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=max(1, min(int(timeout), 300)),
        )
        output = result.stdout.strip() or result.stderr.strip()
        if output:
            return output
        return "命令已成功执行（无打印输出）。" if result.returncode == 0 else f"命令执行失败，退出码: {result.returncode}"
    except subprocess.TimeoutExpired:
        return f"[超时] 命令在 {timeout} 秒内未完成。"
    except Exception as error:
        return f"命令执行异常: {error}"


def run_powershell(command: str = "") -> str:
    """兼容旧工具名；Linux 环境会自动路由到 Bash。"""
    return run_command(command)


def _find_script(script_name: str) -> Path | None:
    if Path(script_name).name != script_name:
        return None
    candidates = [SCRIPTS_DIR / script_name]
    candidates.extend(skill_dir / "scripts" / script_name for skill_dir in SKILLS_DIR.glob("*"))
    return next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)


def run_script(script_name: str = "", args: str = "", timeout: int = 120) -> str:
    """执行项目内诊断脚本；脚本以当前平台解释器运行。"""
    if not script_name.strip():
        return "[参数错误] run_script 缺少必要参数 script_name。"

    target_script = _find_script(script_name)
    if not target_script:
        return f"[错误] 未能定位诊断脚本: {script_name}"
    if not is_cmd_safe(f"{target_script} {args}"):
        return "[安全拦截] 脚本调用包含高危指令，拒绝执行。"

    rejected = _confirm(f"{target_script} {args}".strip())
    if rejected:
        return rejected

    try:
        parsed_args = shlex.split(args, posix=not IS_WINDOWS) if args else []
    except ValueError as error:
        return f"[参数错误] 脚本参数格式无效: {error}"

    suffix = target_script.suffix.lower()
    if IS_WINDOWS and suffix in {".ps1", ".psm1"}:
        invocation = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(target_script), *parsed_args]
    elif suffix in {".sh", ".bash"}:
        invocation = ["bash", str(target_script), *parsed_args]
    elif suffix == ".py":
        invocation = ["python", str(target_script), *parsed_args]
    else:
        return f"[错误] 不支持的脚本类型: {suffix or '无扩展名'}"

    try:
        result = subprocess.run(
            invocation,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=max(1, min(int(timeout), 300)),
        )
        output = result.stdout.strip() or result.stderr.strip()
        if output:
            return output
        return "脚本已成功执行（无打印输出）。" if result.returncode == 0 else f"脚本执行失败，退出码: {result.returncode}"
    except subprocess.TimeoutExpired:
        return f"[超时] 脚本在 {timeout} 秒内未完成。"
    except Exception as error:
        return f"脚本执行异常: {error}"
