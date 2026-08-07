import json
import socket
import platform
from pathlib import Path
from typing import Dict, Any, List
from agent.config import MEMORY_DIR

class MemoryManager:
    def __init__(self):
        self.machines_dir = MEMORY_DIR / 'machines'
        self.knowledge_dir = MEMORY_DIR / 'knowledge'
        self.episodes_dir = MEMORY_DIR / 'episodes'
        
        for d in [self.machines_dir, self.knowledge_dir, self.episodes_dir]:
            d.mkdir(parents=True, exist_ok=True)
            
        self.machine_id = socket.gethostname()
        self.machine_file = self.machines_dir / f'{self.machine_id}.json'

    def get_machine_info(self) -> Dict[str, Any]:
        info = {
            'hostname': self.machine_id,
            'os': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor()
        }
        if self.machine_file.exists():
            try:
                data = json.loads(self.machine_file.read_text(encoding='utf-8'))
                info.update(data)
            except Exception:
                pass
        else:
            self.save_machine_info(info)
        return info

    def save_machine_info(self, data: Dict[str, Any]) -> None:
        self.machine_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def search_knowledge(self, query: str = '') -> List[str]:
        results = []
        for file in self.knowledge_dir.glob('*.md'):
            text = file.read_text(encoding='utf-8')
            if not query or query.lower() in text.lower():
                results.append(f'--- {file.name} ---\n{text}')
        return results

    def add_knowledge(self, title: str, content: str) -> str:
        filename = f"{title.replace(' ', '_')}.md"
        file_path = self.knowledge_dir / filename
        file_path.write_text(content, encoding='utf-8')
        return f'????????: {file_path.name}'

    def add_episode(self, issue: str, resolution: str, status: str = 'success') -> str:
        import time
        ts = int(time.time())
        file_path = self.episodes_dir / f'episode_{ts}.json'
        data = {
            'timestamp': ts,
            'machine': self.machine_id,
            'issue': issue,
            'resolution': resolution,
            'status': status
        }
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return f'???????: {file_path.name}'

    def get_memory_summary(self) -> str:
        info = self.get_machine_info()
        knowledges = list(self.knowledge_dir.glob('*.md'))
        episodes = list(self.episodes_dir.glob('*.json'))
        summary = f"[????] ??: {info['hostname']} | ??: {info['os']} {info['release']} ({info['architecture']})\n"
        summary += f"[?????] {len(knowledges)} ? | [??????] {len(episodes)} ?"
        return summary
