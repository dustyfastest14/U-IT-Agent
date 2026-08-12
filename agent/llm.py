import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI
from agent.config import API_BASE, API_KEY, MODEL, BASE_DIR, MAX_TOOL_ROUNDS
from agent.memory import MemoryManager
from agent.skills import SkillManager
import agent.tools.system as sys_tools
import agent.tools.shell as shell_tools

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_crash_records",
            "description": "专用死机与崩溃排查工具：获取系统历史死机/强制关机(Kernel-Power 41)、意外关机(6008)、蓝屏BugCheck(1001)事件及DMP转储文件 (只读自动放行)",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_count": {"type": "integer", "description": "获取最多事件条数，默认 20"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_processes",
            "description": "获取系统当前运行的进程列表及 CPU/内存占用 (只读自动放行)",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "筛选进程关键词，如 chrome, python"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_services",
            "description": "获取 Windows 系统服务状态列表 (只读自动放行)",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "筛选服务关键词，如 wuauserv"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_disk_memory",
            "description": "获取磁盘各分区剩余空间及系统物理内存使用率 (只读自动放行)",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_event_errors",
            "description": "获取最近 N 小时内的系统与应用 Error/Critical 级别错误事件日志 (只读自动放行)",
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
            "name": "get_machine_history",
            "description": "查询当前设备过去发生过的故障诊断历史记录与修复摘要 (只读自动放行)",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词，如 死机, 关机, 网络"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "test_network",
            "description": "测试 Ping / 网络节点连通性 (只读自动放行)",
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
            "description": "安全执行单条 PowerShell 诊断或修复命令（只读查询类命令自动放行，修改类操作提示用户确认）",
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
            "description": "读取特定配置文件或日志文件 (只读自动放行)",
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
        self.client = OpenAI(base_url=API_BASE, api_key=API_KEY or "none")
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

    def _clean_tool_preview(self, text: str) -> str:
        """格式化工具返回内容，避免只打印 [ 这种视觉误导"""
        lines = [line.strip() for line in text.splitlines() if line.strip() and line.strip() not in ('[', '{', ']', '}')]
        if not lines:
            return "成功执行（返回空集或无匹配）"
        first = lines[0]
        if len(first) > 90:
            first = first[:90] + "..."
        return first

    def chat_loop(self, messages: List[Dict[str, Any]]) -> (str, list):
        sys_content = self._build_system_context()
        full_messages = [{"role": "system", "content": sys_content}] + messages
        executed_tools_log = []
        
        for round_idx in range(MAX_TOOL_ROUNDS):
            try:
                stream = self.client.chat.completions.create(
                    model=MODEL,
                    messages=full_messages,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto",
                    stream=True
                )
            except Exception as e:
                err_msg = f"[API 调用异常]: {str(e)}"
                print(f"\n{err_msg}")
                return err_msg, executed_tools_log
            
            tool_calls_dict = {}
            collected_content = ""
            printed_header = False
            
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                
                # 文本流式打字机输出
                if delta.content:
                    if not printed_header:
                        print("\n[Agent 诊断回复]:\n", end="", flush=True)
                        printed_header = True
                    print(delta.content, end="", flush=True)
                    collected_content += delta.content
                
                # 工具调用分片重组
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls_dict:
                            tool_calls_dict[idx] = {
                                "id": tc_delta.id or "",
                                "type": "function",
                                "function": {
                                    "name": (tc_delta.function.name or "") if tc_delta.function else "",
                                    "arguments": (tc_delta.function.arguments or "") if tc_delta.function else ""
                                }
                            }
                        else:
                            if tc_delta.id:
                                tool_calls_dict[idx]["id"] += tc_delta.id
                            if tc_delta.function:
                                if tc_delta.function.name:
                                    tool_calls_dict[idx]["function"]["name"] += tc_delta.function.name
                                if tc_delta.function.arguments:
                                    tool_calls_dict[idx]["function"]["arguments"] += tc_delta.function.arguments

            if printed_header:
                print()

            # ----------------------------------------------------
            # 关键过滤：清洗丢弃中转站产生的 Ghost/残缺空 Tool Call
            # ----------------------------------------------------
            valid_tool_calls = []
            if tool_calls_dict:
                for idx in sorted(tool_calls_dict.keys()):
                    tc = tool_calls_dict[idx]
                    fn_name = tc.get("function", {}).get("name", "").strip()
                    # 必须具备合法的函数名称才视为有效调用
                    if fn_name:
                        if not tc.get("id"):
                            tc["id"] = f"call_{idx}_{round_idx}"
                        valid_tool_calls.append(tc)

            # 如果存在合法工具调用
            if valid_tool_calls:
                full_messages.append({
                    "role": "assistant",
                    "content": collected_content if collected_content else None,
                    "tool_calls": valid_tool_calls
                })
                
                for tc in valid_tool_calls:
                    fn_name = tc["function"]["name"]
                    raw_args = tc["function"]["arguments"]
                    try:
                        fn_args = json.loads(raw_args) if raw_args.strip() else {}
                    except Exception:
                        fn_args = {}
                    
                    print(f"\n -> [Agent 调用工具]: {fn_name}({fn_args})")
                    tool_res = self._execute_tool(fn_name, fn_args)
                    
                    preview = self._clean_tool_preview(str(tool_res))
                    print(f"    └─ [工具返回]: {preview}")
                    
                    executed_tools_log.append(f"{fn_name}({fn_args})")
                    
                    full_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": str(tool_res)
                    })
            else:
                return collected_content if collected_content else "（代理未返回文本内容）", executed_tools_log

        # 达到轮次上限时的兜底总结
        print("\n[*] 工具调用轮次已达上限，正在为您生成综合诊断总结...")
        full_messages.append({
            "role": "user",
            "content": "请根据上面已收集到的所有系统检查、事件日志与工具返回结果，直接给出完整的排查诊断结论与修复方案。"
        })
        try:
            stream = self.client.chat.completions.create(
                model=MODEL,
                messages=full_messages,
                stream=True
            )
            print("\n[Agent 诊断总结]:\n", end="", flush=True)
            summary_content = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    txt = chunk.choices[0].delta.content
                    print(txt, end="", flush=True)
                    summary_content += txt
            print()
            return summary_content or "（诊断结束）", executed_tools_log
        except Exception as e:
            err_msg = f"诊断轮次达到上限，生成总结时异常: {str(e)}"
            print(f"\n{err_msg}")
            return err_msg, executed_tools_log

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        try:
            if not isinstance(args, dict):
                args = {}
            if name == "get_crash_records":
                return sys_tools.get_crash_records(**args)
            elif name == "get_processes":
                return sys_tools.get_processes(**args)
            elif name == "get_services":
                return sys_tools.get_services(**args)
            elif name == "get_disk_memory":
                return sys_tools.get_disk_memory()
            elif name == "get_event_errors":
                return sys_tools.get_event_errors(**args)
            elif name == "get_machine_history":
                return self.memory_mgr.search_machine_history(**args)
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
        except Exception as e:
            return f"[工具执行异常 ({name})]: {str(e)}"
