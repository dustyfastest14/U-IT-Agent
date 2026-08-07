import json
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI
from agent.config import API_BASE, API_KEY, MODEL, BASE_DIR
from agent.memory import MemoryManager
from agent.skills import SkillManager
import agent.tools.system as sys_tools
import agent.tools.shell as shell_tools

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_processes",
            "description": "??????????????????????",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "?????????????"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_services",
            "description": "?? Windows ???????????????",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "?????????????"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_disk_memory",
            "description": "???????????????????????",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_event_errors",
            "description": "????? N ?????? Error ????",
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {"type": "integer", "description": "??????????? 24"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "test_network",
            "description": "?? Ping / ?????????",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "???????? IP?? www.baidu.com"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_powershell",
            "description": "?????????? PowerShell ?????????",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "PowerShell ????"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_script",
            "description": "??????????? scripts/ ? skill/scripts/ ??",
            "parameters": {
                "type": "object",
                "properties": {
                    "script_name": {"type": "string", "description": "??????? check_net.ps1"},
                    "args": {"type": "string", "description": "???????????"}
                },
                "required": ["script_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "?????????????",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "?????????"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_report",
            "description": "????????????? workspace ??",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "??????? report-network.md"},
                    "content": {"type": "string", "description": "Markdown ??????"}
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": "????????????????????",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Skill ?????"}
                },
                "required": ["skill_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "install_skill",
            "description": "??????? zip ?????? Skill ???????",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_path": {"type": "string", "description": "?????"}
                },
                "required": ["source_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_knowledge",
            "description": "???????????????????",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "????"},
                    "content": {"type": "string", "description": "??????????? Markdown ??"}
                },
                "required": ["title", "content"]
            }
        }
    }
]

class AgentEngine:
    def __init__(self, memory: MemoryManager, skills: SkillManager):
        self.memory = memory
        self.skills = skills
        self.client = OpenAI(base_url=API_BASE, api_key=API_KEY if API_KEY else "dummy")
        self.system_prompt_template = (BASE_DIR / "agent" / "prompts" / "system.md").read_text(encoding="utf-8")

    def build_system_message(self, active_skill_content: str = "") -> Dict[str, str]:
        mem_summary = self.memory.get_memory_summary()
        skills_summary = self.skills.get_skills_summary()
        
        full_system = f"{self.system_prompt_template}\n\n"
        full_system += f"??????????\n{mem_summary}\n\n"
        full_system += f"??? Skill ???\n{skills_summary}\n"
        
        if active_skill_content:
            full_system += f"\n?????? Skill ???\n{active_skill_content}\n"
            
        return {"role": "system", "content": full_system}

    def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        if tool_name == "get_processes":
            return sys_tools.get_processes(tool_args.get("filter_name", ""))
        elif tool_name == "get_services":
            return sys_tools.get_services(tool_args.get("filter_name", ""))
        elif tool_name == "get_disk_memory":
            return sys_tools.get_disk_memory()
        elif tool_name == "get_event_errors":
            return sys_tools.get_event_errors(tool_args.get("hours", 24))
        elif tool_name == "test_network":
            return sys_tools.test_network(tool_args.get("target", "www.baidu.com"))
        elif tool_name == "run_powershell":
            return shell_tools.run_powershell(tool_args.get("command", ""))
        elif tool_name == "run_script":
            return shell_tools.run_script(tool_args.get("script_name", ""), tool_args.get("args", ""))
        elif tool_name == "read_file":
            return sys_tools.read_file(tool_args.get("path", ""))
        elif tool_name == "write_report":
            return sys_tools.write_report(tool_args.get("filename", ""), tool_args.get("content", ""))
        elif tool_name == "load_skill":
            skill_info = self.skills.load_skill(tool_args.get("skill_name", ""))
            if skill_info:
                return f"????? Skill [{skill_info['name']}] ??:\n{skill_info['content']}"
            return f"?????? Skill [{tool_args.get('skill_name')}]"
        elif tool_name == "install_skill":
            return self.skills.install_skill(tool_args.get("source_path", ""))
        elif tool_name == "add_knowledge":
            return self.memory.add_knowledge(tool_args.get("title", ""), tool_args.get("content", ""))
        else:
            return f"????: {tool_name}"

    def run_turn(self, messages: List[Dict[str, Any]]) -> str:
        max_turns = 10
        current_turn = 0
        
        while current_turn < max_turns:
            current_turn += 1
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto"
            )
            
            msg = response.choices[0].message
            messages.append(msg.model_dump())
            
            if not msg.tool_calls:
                return msg.content or ""
                
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments or "{}")
                print(f"\n[Tool Calling] ??????: {func_name}({func_args})")
                
                result = self.execute_tool(func_name, func_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": str(result)
                })
        return "???????????"
