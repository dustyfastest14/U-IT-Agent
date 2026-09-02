import json
import os
import platform
import socket
import subprocess
from pathlib import Path
from datetime import datetime
from agent.config import MEMORY_DIR, LOGS_DIR

class MemoryManager:
    def __init__(self):
        self.machines_dir = MEMORY_DIR / 'machines'
        self.knowledge_dir = MEMORY_DIR / 'knowledge'
        self.episodes_dir = MEMORY_DIR / 'episodes'
        self.logs_dir = LOGS_DIR
        
        for d in [self.machines_dir, self.knowledge_dir, self.episodes_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self.machine_id = socket.gethostname()
        self.profile_path = self.machines_dir / f"{self.machine_id}.json"
        self._init_profile()

    @staticmethod
    def _linux_release() -> dict:
        release_path = Path("/etc/os-release")
        if not release_path.exists():
            return {}

        values = {}
        for line in release_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
        return values

    def _system_info(self) -> dict:
        system = platform.system()
        info = {
            "os": system,
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": self.machine_id,
        }
        if system == "Linux":
            release = self._linux_release()
            info["distribution"] = release.get("PRETTY_NAME", release.get("NAME", "Linux"))
            try:
                info["kernel"] = subprocess.check_output(["uname", "-r"], text=True).strip()
            except (OSError, subprocess.SubprocessError):
                info["kernel"] = platform.release()
        return info

    def _init_profile(self):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.profile_path.exists():
            data = {
                "machine_id": self.machine_id,
                "system": self._system_info(),
                "first_seen": now_str,
                "last_seen": now_str,
                "history_tags": [],
                "recent_repairs": []
            }
            self.profile_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            return

        try:
            profile = json.loads(self.profile_path.read_text(encoding="utf-8"))
            profile["system"] = self._system_info()
            profile["last_seen"] = now_str
            self.profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, json.JSONDecodeError):
            pass

    def record_episode(self, user_symptom: str, tool_summary: str, diagnosis_conclusion: str, tags: list = None):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ts = int(datetime.now().timestamp())
        
        # 1. 结构化案例记录 JSON
        episode_data = {
            "machine_id": self.machine_id,
            "timestamp": now_str,
            "symptom": user_symptom,
            "tool_summary": tool_summary,
            "conclusion": diagnosis_conclusion,
            "tags": tags or []
        }
        episode_file = self.episodes_dir / f"{self.machine_id}_{ts}.json"
        episode_file.write_text(json.dumps(episode_data, ensure_ascii=False, indent=2), encoding='utf-8')
        
        # 2. 人类可读文本日志追加到 logs/
        log_file = self.logs_dir / f"{self.machine_id}_diagnosis.log"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n[{now_str}] 诊断记录\n")
                f.write(f"问题症状: {user_symptom}\n")
                if tool_summary:
                    f.write(f"执行排查: {tool_summary}\n")
                f.write(f"诊断结论: {diagnosis_conclusion[:400]}\n")
                f.write("-" * 50 + "\n")
        except Exception:
            pass
            
        # 3. 更新机器档案 profile
        try:
            profile = json.loads(self.profile_path.read_text(encoding="utf-8"))
            profile["last_seen"] = now_str
            
            # 自动提炼标签
            current_tags = set(profile.get("history_tags", []))
            if tags:
                for t in tags:
                    if t and len(t) < 20:
                        current_tags.add(t)
            profile["history_tags"] = list(current_tags)
            
            # 记录历史排查条目 (保留最近 15 次)
            repairs = profile.get("recent_repairs", [])
            repairs.insert(0, {
                "time": now_str,
                "symptom": user_symptom[:100],
                "conclusion": diagnosis_conclusion[:200]
            })
            profile["recent_repairs"] = repairs[:15]
            
            self.profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
            return f"诊断记录已归档 (Episode: {episode_file.name})"
        except Exception as e:
            return f"归档失败: {str(e)}"

    def get_summary(self) -> str:
        try:
            profile = json.loads(self.profile_path.read_text(encoding="utf-8"))
            repairs = profile.get("recent_repairs", [])
            knowledges = list(self.knowledge_dir.glob('*.md'))
            k_titles = [k.stem for k in knowledges]
            
            summary_parts = [
                f"当前主机: {self.machine_id}",
                f"系统: {profile.get('system', {}).get('distribution', profile.get('system', {}).get('os', profile.get('os', '未知')))}",
                f"设备历史故障标签: {', '.join(profile.get('history_tags', [])) or '暂无'}"
            ]
            
            if repairs:
                summary_parts.append("本机最近故障排查记录 (可供本次诊断参考):")
                for idx, r in enumerate(repairs[:3], 1):
                    summary_parts.append(f"  {idx}. [{r['time']}] 症状: {r['symptom']} | 结论: {r['conclusion']}")
            else:
                summary_parts.append("本机暂无历史故障记录（首次诊断此机器）。")
                
            if k_titles:
                summary_parts.append(f"全局沉淀知识库: {len(k_titles)} 条 ({', '.join(k_titles[:3])})")
                
            return "\n".join(summary_parts)
        except Exception:
            return f"当前主机: {self.machine_id}"

    def search_machine_history(self, keyword: str = '') -> str:
        try:
            profile = json.loads(self.profile_path.read_text(encoding="utf-8"))
            repairs = profile.get("recent_repairs", [])
            if not repairs:
                return f"主机 {self.machine_id} 暂无历史诊断记录。"
            
            results = []
            for r in repairs:
                if not keyword or keyword.lower() in r['symptom'].lower() or keyword.lower() in r['conclusion'].lower():
                    entry = f"[{r['time']}]\n  症状: {r['symptom']}\n  结论: {r['conclusion']}"
                    results.append(entry)
            
            if not results:
                return f"未找到与 '{keyword}' 匹配的历史诊断记录。"
            return f"--- 主机 {self.machine_id} 历史诊断记录 ---\n" + "\n\n".join(results)
        except Exception as e:
            return f"查询历史记录失败: {str(e)}"

    def write_knowledge(self, title: str, content: str):
        safe_title = "".join([c for c in title if c.isalnum() or c in ('-', '_')]).rstrip()
        if not safe_title:
            safe_title = f"knowledge_{int(datetime.now().timestamp())}"
        k_path = self.knowledge_dir / f"{safe_title}.md"
        k_path.write_text(content, encoding='utf-8')
        return f"排查经验知识已沉淀归档至: {k_path.name}"
