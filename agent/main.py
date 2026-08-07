import sys
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

def main():
    if not API_KEY or API_KEY == "your_actual_api_key_here":
        print("[!] 警告: 未在 .env 中检测到有效的 API_KEY。网络推理可能会失败。")
        print("    请编辑根目录下的 .env 配置文件填入真实的 API 密钥。")
    
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
            print("  /memory        - 查看当前主机记忆摘要")
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
            print(f"\n[记忆状态]: {memory_mgr.get_summary()}\n")
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
        reply = engine.chat_loop(messages)
        print(f"\n[Agent 诊断回复]:\n{reply}")
        
        messages.append({"role": "assistant", "content": reply})

if __name__ == '__main__':
    main()