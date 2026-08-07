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
            "description": "获取系统当前运行的进程列表及 CPU/内存占用",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "筛选进程关键词"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_services",
            "description": "获取 Windows 系统服务状态列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "筛选服务关键词"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_disk_memory",
            "description": "获取磁盘各分区剩余空间及系统物理内存使用率",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_event_errors",
            "description": "获取最近 N 小时内的系统与应用 Error 错误日志",
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {"type": "integer", "description": "检索小时数，默认 24"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "test_network",
            "description": "测试 Ping / 网络节点连通性",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "目标主机 IP 或域名，如 www.baidu.com"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_powershell",
            "description": "受限安全执行单条 PowerShell 诊断或修复命令",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "PowerShell 命令"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_script",
            "description": "受限执行预置诊断脚本 (scripts/ 或 skill/scripts/ 路径)",
            "parameters": {
                "type": "object",
                "properties": {
                    "script_name": {"type": "string", "description": "脚本名称，如 check_net.ps1"},
                    "args": {"type": "string", "description": "传给脚本的附加参数"}
                },
                "required": ["script_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取特定配置文件或日志文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件绝对或相对路径"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_report",
            "description": "将诊断结论生成 Markdown 格式报告写入 workspace 目录",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "报告文件名，如 report-net.md"},
                    "content": {"type": "string", "description": " Markdown 报告正文内容"}
                },
                "required": ["filename", "content"]
            }
        }
    }
]

class LLMEngine:
    def __init__(self, memory_mgr: MemoryManager, skill_mgr: SkillManager):
        self.client = OpenAI(base_url=API_BASE, api_key=API_KEY)
        self.memory_mgr = memory_mgr
        self.skill_mgr = skill_mgr
        
        sys_prompt_path = BASE_DIR / 'agent' / 'prompts' / 'system.md'
        self.base_sys_prompt = sys_prompt_path.read_text(encoding='utf-8')

    def _build_system_context(self) -> str:
        mem_summary = self.memory_mgr.get_summary()
        skills = self.skill_mgr.scan_skills()
        skills_summary = "\n".join([f"- {s['name']}: {s['description']}" for s in skills]) if skills else "暂未加载特定 Skill。"
        
        full_sys = f"{self.base_sys_prompt}\n\n# 长期记忆与环境上下文\n{mem_summary}\n\n# 已可用技能 Skill 列表\n{skills_summary}"
        return full_sys

    def chat_loop(self, messages: List[Dict[str, Any]]) -> str:
        sys_content = self._build_system_context()
        full_messages = [{"role": "system", "content": sys_content}] + messages
        
        for _ in range(5):  # Tool Calling 交互迭代最多 5 轮
            try:
                response = self.client.chat.completions.create(
                    model=MODEL,
                    messages=full_messages,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto"
                )
            except Exception as e:
                return f"[API 调用异常]: {str(e)}"
            
            msg = response.choices[0].message
            full_messages.append(msg.model_dump())
            
            if not msg.tool_calls:
                return msg.content if msg.content else "（代理未返回文本内容）"
            
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments)
                except Exception:
                    fn_args = {}
                
                print(f" -> [Agent 调用工具]: {fn_name}({fn_args})")
                tool_res = self._execute_tool(fn_name, fn_args)
                
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(tool_res)
                })
        return "Tool Calling 达到轮次上限，强制中断循环。"

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        if name == "get_processes":
            return sys_tools.get_processes(**args)
        elif name == "get_services":
            return sys_tools.get_services(**args)
        elif name == "get_disk_memory":
            return sys_tools.get_disk_memory()
        elif name == "get_event_errors":
            return sys_tools.get_event_errors(**args)
        elif name == "test_network":
            return sys_tools.test_network(**args)
        elif name == "read_file":
            return sys_tools.read_file(**args)
        elif name == "write_report":
            return sys_tools.write_report(**args)
        elif name == "run_powershell":
            return shell_tools.run_powershell(**args)
        elif name == "run_script":
            return shell_tools.run_script(**args)
        else:
            return f"未知工具名称: {name}"