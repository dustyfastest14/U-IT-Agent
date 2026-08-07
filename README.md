# U-IT-Agent (Windows 诊断与修复 Agent)

> 一款专为 **Windows** 环境设计、支持 **U 盘便携使用** 的 AI 系统/软件故障诊断与排查 Agent。

---

## 💡 核心特性

- **双击即用**：提供 Windows `启动.bat` 批处理入口，无需复杂命令行配置。
- **OpenAI 兼容 API**：支持任意 OpenAI 兼容的 LLM 接口，借助 Tool Calling 实现多轮智能诊断决策。
- **只读诊断与安全确认**：
  - 默认优先使用只读系统工具收集进程、服务、磁盘/内存、事件日志及网络连通性。
  - 涉及到修改注册表、停止/禁用服务或运行脚本时，强制弹出 `[y/N]` 安全确认提示，防止误操作。
- **记忆与自我进化**：
  - **机器档案**：基于主机指纹记录设备历史故障与系统属性。
  - **经验沉淀**：诊断成功后自动蒸馏并保存排查知识与历史案例。
- **Skill 技能插件架构**：支持动态扫描、加载和一键安装本地或 `.zip` 压缩包格式的排查技能包。

---

## 📂 项目结构

```text
U-IT-Agent/
├── 启动.bat                 # Windows 一键启动脚本
├── README.md               # 项目使用与架构文档
├── requirements.txt        # Python 依赖包列表
├── .env.example            # 环境变量配置模板
├── .gitignore              # Git 忽略规则
├── agent/                  # Agent 核心实现
│   ├── config.py           # 配置加载与安全关键词白名单/黑名单
│   ├── llm.py              # OpenAI API 客户端 & Tool Calling 轮次控制 Loop
│   ├── main.py             # CLI REPL 交互入口与快捷指令解析
│   ├── memory.py           # 机器档案与知识库存储管理
│   ├── skills.py           # Skill 扫描、加载与本地/Zip 安装器
│   ├── prompts/
│   │   └── system.md       # 系统 Prompt 与排查行为规范
│   └── tools/
│       ├── system.py       # 内置只读系统诊断工具集 (进程/服务/磁盘/日志/网络)
│       └── shell.py        # 受限 PowerShell / 脚本执行器 (带安全提示确认)
├── skills/                 # 可扩展 Skill 技能包目录
│   └── _example-network-diag/
│       └── SKILL.md        # 示例网络诊断 Skill 包
├── scripts/                # 全局预置 PowerShell 诊断脚本目录
│   └── check_net.ps1       # 示例网络深入排查 PowerShell 脚本
├── memory/                 # 长期记忆与经验存储
│   ├── machines/           # 主机档案
│   ├── knowledge/          # 沉淀的 Markdown 经验知识库
│   └── episodes/           # 历史排查案例 JSON
├── workspace/              # 报告与临时输出区 (Markdown 诊断报告)
└── logs/                   # 日志目录
```

---

## 🚀 快速开始

### 1. 环境依赖

- Windows 10 / 11 / Server
- Python 3.10+（如果使用便携 Python，放至 `python/` 目录即可）

### 2. 安装 Python 依赖

```powershell
pip install -r requirements.txt
```

### 3. 配置 API 密钥

复制项目根目录下的 `.env.example` 并重命名为 `.env`：

```ini
API_BASE=https://api.openai.com/v1
API_KEY=your_actual_api_key_here
MODEL=gpt-4o
CONFIRM_MODE=true
```

> **注意**：若运行在内网环境且 API 接口需要代理访问，可确保本机相关 HTTP/HTTPS 代理配置正常。

### 4. 运行 Agent

双击根目录下的 **`启动.bat`**，或在命令行中运行：

```powershell
python agent/main.py
```

---

## 💬 常用快捷指令

在交互命令行 (`U-IT-Agent>`) 中，除直接输入自然语言提问（如“微信打不开”、“网络连不上”、“C 盘满了”）外，还支持以下快捷指令：

| 指令 | 说明 |
| :--- | :--- |
| `/help` | 查看帮助文档与命令说明 |
| `/skills` | 列出当前已扫描并安装的所有 Skill 技能插件 |
| `/memory` | 查看当前主机的档案信息与沉淀知识摘要 |
| `/install <path>` | 从本地文件夹路径或 `.zip` 压缩包安装新 Skill 插件 |
| `/clear` | 清空并重置当前对话上下文 |
| `/quit` | 退出程序 |

---

## 🔒 安全设计规则

1. **高危命令拦截**：内置高危 PowerShell 命令过滤规则（如 `format`、`rmdir /s /q c:` 等），强行拦截破坏性命令。
2. **读写分离与沙箱**：诊断输出报告与临时文件强制限定写入至 `workspace/` 路径下。
3. **交互确认**：当开启 `CONFIRM_MODE=true` 时，任何执行脚本或修改命令必须显示完整命令并得到用户明确输入的 `y` 方可运行。

---

## 📄 开源许可

本项目遵循 MIT 许可证。
