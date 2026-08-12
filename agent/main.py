import sys
import os
import re
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent.memory import MemoryManager
from agent.skills import SkillManager
from agent.llm import LLMEngine
from agent.config import API_KEY, API_BASE, MODEL

def print_banner():
    print("=" * 60)
    print("      U-IT-Agent (Windows 便携 AI 诊断助手 MVP)")
    print(f"      API Gateway: {API_BASE}")
    print(f"      Model Name : {MODEL}")
    print("      输入 /help 查看指令 | 输入 /quit 退出对话")
    print("=" * 60)

def extract_tags(text: str) -> list:
    tags = []
    keywords = ["死机", "蓝屏", "关机", "重启", "卡顿", "网络", "DNS", "内存", "CPU", "磁盘", "Kernel-Power", "驱动", "微信", "服务"]
    for kw in keywords:
        if kw.lower() in text.lower():
            tags.append(kw)
    return tags

def main():
    if not API_KEY or API_KEY == "your_actual_api_key_here":
        print("[!] 警告: 未在 .env 中检测到有效的 API_KEY。网络推理可能会失败。")
        print("    请在项目根目录下创建 .env 文件并填入真实的 API 密钥。")
    
    memory_mgr = MemoryManager()
    skill_mgr = SkillManager()
    engine = LLMEngine(memory_mgr, skill_mgr)
    
    print_banner()
    messages = []
    
    while True:
        try:
            user_input = input("\nU-IT-Agent> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n退出程序。")
            break
        
        if not user_input:
            continue
        
        # 快捷指令解析
        if user_input.lower() in ('/quit', '/exit'):
            print("感谢使用，再见！")
            break
        elif user_input.lower() == '/help':
            print("\n[帮助菜单]")
            print("  /skills        - 列出已发现和安装的技能包")
            print("  /memory        - 查看当前主机的档案信息与历史诊断记录")
            print("  /install <path>- 安装本地文件夹或 Zip 格式技能包")
            print("  /clear         - 清空当前对话上下文")
            print("  /quit          - 退出助手\n")
            continue
        elif user_input.lower() == '/skills':
            skills = skill_mgr.scan_skills()
            print("\n[当前可用 Skills 列表]:")
            if not skills:
                print("  暂无安装的 Skill。")
            for s in skills:
                print(f"  - {s['name']}: {s['description']}")
            print()
            continue
        elif user_input.lower() == '/memory':
            print(f"\n[本机记忆与档案状态]:\n{memory_mgr.get_summary()}\n")
            continue
        elif user_input.lower().startswith('/install '):
            target_path = user_input[9:].strip()
            res = skill_mgr.install_skill(target_path)
            print(f"\n[Skill 安装结果]: {res}\n")
            continue
        elif user_input.lower() == '/clear':
            messages = []
            print("\n已清空上下文历史记录。\n")
            continue
        
        messages.append({"role": "user", "content": user_input})
        
        print("\nAgent 正在诊断排查中...")
        reply, tool_logs = engine.chat_loop(messages)
        messages.append({"role": "assistant", "content": reply})
        
        # 自动将诊断会话归档至本机档案与 logs/ 目录
        if reply and not reply.startswith("[API 调用异常]"):
            auto_tags = extract_tags(user_input + " " + reply)
            tool_summary = ", ".join(tool_logs) if tool_logs else "直接分析"
            arch_res = memory_mgr.record_episode(
                user_symptom=user_input,
                tool_summary=tool_summary,
                diagnosis_conclusion=reply,
                tags=auto_tags
            )
            print(f"\n[✓ 诊断记录已自动归档至本机档案 memory/machines/{memory_mgr.machine_id}.json 与 logs/ 目录]")

if __name__ == '__main__':
    main()
