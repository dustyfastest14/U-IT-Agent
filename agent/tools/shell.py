import subprocess
from pathlib import Path
from agent.config import CONFIRM_MODE, FORBIDDEN_KEYWORDS, SCRIPTS_DIR, SKILLS_DIR

def run_powershell(command: str) -> str:
    for kw in FORBIDDEN_KEYWORDS:
        if kw in command.lower():
            return f"????: ??????????? '{kw}'????????"

    if CONFIRM_MODE:
        print(f"\n[????] Agent ???? PowerShell ??:")
        print(f"----------------------------------------")
        print(f"{command}")
        print(f"----------------------------------------")
        choice = input("???????(y/N): ").strip().lower()
        if choice != 'y':
            return "??????? PowerShell ???"

    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
        output = res.stdout
        if res.stderr:
            output += f"\n[StdErr]\n{res.stderr}"
        return output if output else "???????????????"
    except Exception as e:
        return f"??????: {str(e)}"

def run_script(script_name: str, args: str = '') -> str:
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        found = False
        for sdir in SKILLS_DIR.glob('*/scripts'):
            candidate = sdir / script_name
            if candidate.exists():
                script_path = candidate
                found = True
                break
        if not found:
            return f"??: ????? {script_name}???? global scripts ? skills scripts?"

    full_cmd = f"& '{script_path}' {args}"
    return run_powershell(full_cmd)
