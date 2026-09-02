import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

API_BASE = os.getenv('API_BASE', 'https://api.openai.com/v1')
API_KEY = os.getenv('API_KEY', '')
MODEL = os.getenv('MODEL', 'gpt-4o')
CONFIRM_MODE = os.getenv('CONFIRM_MODE', 'true').lower() == 'true'
MAX_TOOL_ROUNDS = int(os.getenv('MAX_TOOL_ROUNDS', '15'))

SKILLS_DIR = BASE_DIR / 'skills'
SCRIPTS_DIR = BASE_DIR / 'scripts'
MEMORY_DIR = BASE_DIR / 'memory'
WORKSPACE_DIR = BASE_DIR / 'workspace'
LOGS_DIR = BASE_DIR / 'logs'

for d in [SKILLS_DIR, SCRIPTS_DIR, MEMORY_DIR, WORKSPACE_DIR, LOGS_DIR] + [MEMORY_DIR / x for x in ['machines', 'episodes', 'knowledge']]:
    d.mkdir(parents=True, exist_ok=True)

FORBIDDEN_KEYWORDS = [
    # Windows 高危破坏性指令
    'format ', 'rmdir /s /q c:', 'del /f /s /q c:', 'remove-item -recurse -force c:',
    # Linux 高危破坏性指令
    'rm -rf /', 'rm -fr /', 'rm -rf /:', 'rm -fr /*', 'mkfs', 'dd if=',
    ':(){ :|:& };:', '> /dev/sda', '> /dev/nvme', '> /dev/vda', 'chmod -R 777 /',
    'shutdown -h now', 'init 0', 'poweroff', 'mkfs.ext4', 'mkfs.xfs'
]
