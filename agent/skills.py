import os
import shutil
import zipfile
from pathlib import Path
from agent.config import SKILLS_DIR

class SkillManager:
    def __init__(self):
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    def scan_skills(self) -> list:
        skills = []
        for item in SKILLS_DIR.glob('*'):
            if item.is_dir():
                skill_md = item / 'SKILL.md'
                if skill_md.exists():
                    skills.append({
                        "name": item.name,
                        "path": str(item),
                        "description": self._parse_skill_desc(skill_md)
                    })
        return skills

    def _parse_skill_desc(self, md_path: Path) -> str:
        try:
            lines = md_path.read_text(encoding='utf-8').splitlines()
            for line in lines:
                if line.startswith('description:') or line.startswith('name:'):
                    return line
            return lines[0] if lines else "无描述"
        except Exception:
            return "解析描述失败"

    def load_skill_detail(self, skill_name: str) -> str:
        target = SKILLS_DIR / skill_name / 'SKILL.md'
        if target.exists():
            return target.read_text(encoding='utf-8')
        return f"未找到技能包 {skill_name} 的 SKILL.md 文档。"

    def install_skill(self, source_path: str) -> str:
        src = Path(source_path)
        if not src.exists():
            return f"[错误] 指定安装路径不存在: {source_path}"
        
        if src.is_dir():
            dest = SKILLS_DIR / src.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            return f"成功安装技能包文件夹: {src.name}"
        elif src.suffix.lower() == '.zip':
            with zipfile.ZipFile(src, 'r') as zip_ref:
                zip_ref.extractall(SKILLS_DIR)
            return f"成功解压并安装技能包 Zip: {src.name}"
        else:
            return "[错误] 不支持的技能包格式（仅支持文件夹或 .zip 压缩包）。"