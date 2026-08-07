import sys
from pathlib import Path

# ???????? sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from agent.config import API_KEY, MODEL, API_BASE, CONFIRM_MODE
from agent.memory import MemoryManager
from agent.skills import SkillManager
from agent.llm import AgentEngine

def print_banner():
    print("=" * 65)
    print("        U-IT-Agent (Windows ??????? MVP)          ")
    print("=" * 65)
    print(f"[*] API Base: {API_BASE}")
    print(f"[*] Model   : {MODEL}")
    print(f"[*] ???? : {'?? (?????????)' if CONFIRM_MODE else '??'}")
    print("?? '/help' ??????????? '/quit' ??")
    print("-" * 65)

def main():
    print_banner()
    
    if not API_KEY or API_KEY == "your-api-key-here":
        print("[!] ??: ?? .env ??????? API_KEY??? LLM ??????")
        print("[!] ??? .env ??? API_KEY ??????\n")

    memory = MemoryManager()
    skills = SkillManager()
    engine = AgentEngine(memory, skills)
    
    messages = [engine.build_system_message()]

    while True:
        try:
            user_input = input("\nU-IT-Agent> ").strip()
            if not user_input:
                continue
                
            if user_input.lower() in ['/quit', '/exit']:
                print("[!] ???? U-IT-Agent????")
                break
            elif user_input.lower() == '/help':
                print("\n????:")
                print("  /help           ???????")
                print("  /skills         ??????????")
                print("  /memory         ?????????????")
                print("  /install <path> ?????? zip ??????")
                print("  /clear          ???????")
                print("  /quit           ????")
                continue
            elif user_input.lower() == '/skills':
                print(f"\n{skills.get_skills_summary()}")
                continue
            elif user_input.lower() == '/memory':
                print(f"\n{memory.get_memory_summary()}")
                continue
            elif user_input.lower().startswith('/install '):
                src_path = user_input.split(' ', 1)[1].strip()
                res = skills.install_skill(src_path)
                print(f"\n{res}")
                # ?????????
                messages[0] = engine.build_system_message()
                continue
            elif user_input.lower() == '/clear':
                messages = [engine.build_system_message()]
                print("\n[!] ?????????")
                continue

            messages.append({"role": "user", "content": user_input})
            print("\n[Agent ???...]")
            
            reply = engine.run_turn(messages)
            print(f"\n[Agent ?????]:\n{reply}")

        except KeyboardInterrupt:
            print("\n[!] ????????????")
            break
        except Exception as e:
            print(f"\n[!] ????: {str(e)}")

if __name__ == '__main__':
    main()
