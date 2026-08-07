import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from agent.config import SKILLS_DIR

class SkillManager:
    def __init__(self):
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    def list_skills(self) -> List[Dict[str, str]]:
        skills = []
        for d in SKILLS_DIR.iterdir():
            if d.is_dir() and not d.name.startswith('.'):
                skill_md = d / 'SKILL.md'
                if skill_md.exists():
                    desc = self._extract_description(skill_md)
                    skills.append({
                        'name': d.name,
                        'path': str(d),
                        'description': desc
                    })
        return skills

    def _extract_description(self, skill_md: Path) -> str:
        try:
            lines = skill_md.read_text(encoding='utf-8').splitlines()
            for line in lines:
                if line.startswith('# ??:') or line.startswith('# description:') or line.startswith('??:') or line.startswith('description:'):
                    return line.split(':', 1)[1].strip()
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    return line.strip()[:100]
        except Exception:
            pass
        return '?????'

    def load_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        target_dir = SKILLS_DIR / skill_name
        if not target_dir.exists() or not target_dir.is_dir():
            return None
        
        skill_md = target_dir / 'SKILL.md'
        content = skill_md.read_text(encoding='utf-8') if skill_md.exists() else ''
        
        scripts = []
        scripts_dir = target_dir / 'scripts'
        if scripts_dir.exists() and scripts_dir.is_dir():
            scripts = [s.name for s in scripts_dir.glob('*.ps1')]
            
        return {
            'name': skill_name,
            'content': content,
            'scripts': scripts,
            'path': str(target_dir)
        }

    def install_skill(self, source_path: str) -> str:
        src = Path(source_path)
        if not src.exists():
            return f'??: ?? {source_path} ???'
            
        if src.is_dir():
            target_name = src.name
            target_dir = SKILLS_DIR / target_name
            if target_dir.exists():
                shutil.rmtree(target_dir)
            shutil.copytree(src, target_dir)
            return f'?????????? Skill [{target_name}]'
        elif src.is_file() and src.suffix == '.zip':
            target_name = src.stem
            target_dir = SKILLS_DIR / target_name
            if target_dir.exists():
                shutil.rmtree(target_dir)
            with zipfile.ZipFile(src, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            return f'???? Zip ????? Skill [{target_name}]'
        else:
            return '??: ????????? .zip ???? Skill'

    def get_skills_summary(self) -> str:
        skills = self.list_skills()
        if not skills:
            return '???????????'
        lines = ['[?????????]']
        for s in skills:
            lines.append(f"- {s['name']}: {s['description']}")
        return '\n'.join(lines)
