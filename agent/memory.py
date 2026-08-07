import json
import socket
from pathlib import Path
from datetime import datetime
from agent.config import MEMORY_DIR

class MemoryManager:
    def __init__(self):
        self.machines_dir = MEMORY_DIR / 'machines'
        self.knowledge_dir = MEMORY_DIR / 'knowledge'
        self.episodes_dir = MEMORY_DIR / 'episodes'
        
        self.machines_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.episodes_dir.mkdir(parents=True, exist_ok=True)
        
        self.machine_id = socket.gethostname()
        self.profile_path = self.machines_dir / f"{self.machine_id}.json"
        self._init_profile()

    def _init_profile(self):
        if not self.profile_path.exists():
            data = {
                "machine_id": self.machine_id,
                "os": "Windows",
                "first_seen": datetime.now().isoformat(),
                "history_tags": [],
                "recent_repairs": []
            }
            self.profile_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def get_summary(self) -> str:
        try:
            profile = json.loads(self.profile_path.read_text(encoding='utf-8'))
            knowledges = list(self.knowledge_dir.glob('*.md'))
            k_titles = [k.stem for k in knowledges]
            return f"当前主机: {self.machine_id} | 历史标记: {profile.get('history_tags', [])} | 已沉淀知识点: {len(k_titles)} 个 ({', '.join(k_titles[:3])})"
        except Exception:
            return f"当前主机: {self.machine_id}"

    def write_knowledge(self, title: str, content: str):
        safe_title = "".join([c for c in title if c.isalnum() or c in ('-', '_')]).rstrip()
        if not safe_title:
            safe_title = f"knowledge_{int(datetime.now().timestamp())}"
        k_path = self.knowledge_dir / f"{safe_title}.md"
        k_path.write_text(content, encoding='utf-8')
        return f"排查知识已沉淀归档至: {k_path.name}"