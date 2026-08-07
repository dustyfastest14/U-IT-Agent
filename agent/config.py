import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

API_BASE = os.getenv('API_BASE', 'https://api.openai.com/v1')
API_KEY = os.getenv('API_KEY', '')
MODEL = os.getenv('MODEL', 'gpt-4o')
CONFIRM_MODE = os.getenv('CONFIRM_MODE', 'true').lower() == 'true'

SKILLS_DIR = BASE_DIR / 'skills'
SCRIPTS_DIR = BASE_DIR / 'scripts'
MEMORY_DIR = BASE_DIR / 'memory'
WORKSPACE_DIR = BASE_DIR / 'workspace'
LOGS_DIR = BASE_DIR / 'logs'

FORBIDDEN_KEYWORDS = ['format ', 'rmdir /s /q c:', 'del /f /s /q c:', 'remove-item -recurse -force c:']
