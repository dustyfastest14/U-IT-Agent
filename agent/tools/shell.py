import base64
import concurrent.futures
import platform
import re
import shlex
import subprocess
import threading
import time
import uuid
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


class PersistentPowerShell:
    """保持一个长生命周期的 PowerShell 进程会话，实现快速执行、跨命令变量保留与命令超时中断。"""

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def _start(self):
        try:
            if self._proc and self._proc.poll() is None:
                self._proc.kill()
        except Exception:
            pass
        try:
            self._proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except Exception:
            self._proc = None

    def _read_output(self, token: str) -> str:
        end_marker = f"[__DONE__:{token}]"
        out_parts = []
        err_parts = []
        raw_parts = []
        while True:
            if not self._proc or self._proc.poll() is not None:
                break
            line = self._proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str == end_marker:
                break
            if line_str.startswith("[__OUT_B64__:") and line_str.endswith("]"):
                raw_b64 = line_str[len("[__OUT_B64__:"):-1]
                out_parts.append(base64.b64decode(raw_b64).decode("utf-8", errors="replace"))
            elif line_str.startswith("[__ERR_B64__:") and line_str.endswith("]"):
                raw_b64 = line_str[len("[__ERR_B64__:"):-1]
                err_parts.append(base64.b64decode(raw_b64).decode("utf-8", errors="replace"))
            elif line_str:
                raw_parts.append(line)
        combined = ("".join(raw_parts) + "".join(out_parts) + "".join(err_parts)).strip()
        return combined

    def run(self, cmd: str, timeout: int = 60) -> str:
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                self._start()
            if self._proc is None:
                return ""

            token = uuid.uuid4().hex
            cmd_b64 = base64.b64encode(cmd.encode("utf-8")).decode("ascii")
            ps_line = (
                f". {{ try {{ $raw = . ([ScriptBlock]::Create([System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{cmd_b64}')))); "
                f"$str = $raw | Out-String; if ($str) {{ $b = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($str)); "
                f"[Console]::Out.WriteLine('[__OUT_B64__:' + $b + ']') }} }} "
                f"catch {{ $err = $_ | Out-String; $b = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($err)); "
                f"[Console]::Out.WriteLine('[__ERR_B64__:' + $b + ']') }} "
                f"finally {{ [Console]::Out.WriteLine('[__DONE__:{token}]') }} }}\n"
            )
            try:
                self._proc.stdin.write(ps_line)
                self._proc.stdin.flush()
            except Exception as e:
                self._start()
                return f"[会话异常已重置] 写入命令失败: {e}"

            future = self._executor.submit(self._read_output, token)
            try:
                out = future.result(timeout=max(1, min(int(timeout), 300)))
                return out if out else "命令已成功执行（无打印输出）。"
            except concurrent.futures.TimeoutError:
                try:
                    self._proc.kill()
                except Exception:
                    pass
                self._start()
                return f"[超时] 命令在 {timeout} 秒内未完成，已自动中断并重置会话。"

    def reset(self):
        with self._lock:
            self._start()


_ps_session = PersistentPowerShell() if IS_WINDOWS else None


def reset_shell_session() -> str:
    """重置持久化会话状态。"""
    if _ps_session:
        _ps_session.reset()
        return "PowerShell 持久会话已成功重置。"
    return "非 Windows 平台无持久会话需重置。"


def is_cmd_safe(command: str) -> bool:
    """判断命令是否包含配置中明确禁止的高危操作。"""
    command_lower = command.lower()
    return not any(keyword in command_lower for keyword in FORBIDDEN_KEYWORDS)


def is_query_only_cmd(command: str) -> bool:
    """修改系统状态的命令必须经人工确认。"""
    command_lower = command.lower().strip()
    if re.fullmatch(r"start-sleep(\s+.*)?", command_lower):
        return True
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
    """按当前操作系统执行 PowerShell 或 Bash 命令。Windows 环境优先复用持久化 PowerShell 会话。"""
    if not command.strip():
        return "[参数错误] run_command 缺少必要参数 command。"
    if not is_cmd_safe(command):
        return "[安全拦截] 命令包含禁止的高危操作指令，拒绝执行。"

    rejected = _confirm(command)
    if rejected:
        return rejected

    if IS_WINDOWS and _ps_session is not None:
        try:
            return _ps_session.run(command, timeout=timeout)
        except Exception:
            pass

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
