# U-IT-Agent（Windows / Linux 诊断与修复 Agent）

> 一款支持 **Windows 与 Linux** 的 AI 系统/软件故障诊断与排查 Agent。

[![Release](https://img.shields.io/github/v/release/dustyfastest14/U-IT-Agent?label=Download%20Portable%20Zip&color=blue)](https://github.com/dustyfastest14/U-IT-Agent/releases/latest)

---

## 💡 核心特性

- **跨平台启动**：Windows 使用 `启动.bat`，Linux 使用 `start.sh`。
- **持久化 PowerShell 会话管道**：借鉴 PowerShell MCP 机制，Windows 运维支持常驻会话管道，变量与上下文跨命令保留，执行速度大幅提速（毫秒级响应），支持长命令超时自动中断与故障自愈。
- **专精运维诊断工具集**：
  - **蓝屏与死机排查 (`get_bsod_crashes`)**：一键提取 Minidump 堆栈、Kernel-Power 41 异常关机事件与 BugCheck 停机码自动中文解码。
  - **全盘 BitLocker 检测 (`get_bitlocker_status`)**：免管理员提权检测各卷加密保护状态、转换进度与算法。
- **OpenAI 兼容 API**：支持任意 OpenAI 兼容的 LLM 接口，借助 Tool Calling 实现多轮智能诊断决策。
- **只读诊断与安全确认**：
  - 默认优先使用只读系统工具收集进程、服务、磁盘/内存、Windows 事件日志或 Linux journal/dmesg 及网络连通性。
  - 涉及到修改注册表、停止/禁用服务或运行脚本时，强制弹出 `[y/N]` 安全确认提示，防止误操作。
- **记忆与自我进化**：
  - **机器档案**：基于主机指纹记录设备历史故障与系统属性。
  - **经验沉淀**：诊断成功后自动蒸馏并保存排查知识与历史案例。
- **Skill 技能插件架构**：支持动态扫描、加载和一键安装本地或 `.zip` 压缩包格式的排查技能包。

---

## 🛠️ 内置工具能力清单 (Tool Calling)

Agent 依托 OpenAI 规范的 Function Calling 自动选择并调用以下底层工具进行智能排障：

| 工具名称 | 功能描述 | 平台支持 | 权限与安全性 |
| :--- | :--- | :--- | :--- |
| `get_bsod_crashes` | **蓝屏/死机专精**：解析 Minidump 转储、Kernel-Power 41 异常关机及 BugCheck 停机码中文释义；Linux 下提取 Panic/OOM 记录 | Windows / Linux | 只读自动放行 |
| `get_bitlocker_status` | **磁盘加密专精**：免管理员提权读取全盘 BitLocker 保护状态、转换进度与加密算法；Linux 检查 LUKS 映射 | Windows / Linux | 只读自动放行 |
| `run_command` | **命令执行**：Windows 基于常驻持久化 PowerShell 管道执行（毫秒级、跨命令保留变量与上下文、超时自愈）；Linux 路由至 Bash | Windows / Linux | 只读自动放行；涉及修改需确认 |
| `get_processes` | 检索当前活跃进程列表，按 CPU/内存占用降序排列 | Windows / Linux | 只读自动放行 |
| `get_services` | 检索关键系统服务运行状态与自启动配置 | Windows / Linux | 只读自动放行 |
| `get_disk_memory` | 统计各磁盘挂载分区容量使用率及系统物理内存剩余 | Windows / Linux | 只读自动放行 |
| `get_event_errors` | 查询系统与应用日志中最近 N 小时内的严重 Error/Critical 事件 | Windows / Linux | 只读自动放行 |
| `test_network` | 诊断目标域名/IP 的 DNS 解析、Ping 延迟与连通性 | Windows / Linux | 只读自动放行 |
| `read_file` | 安全读取系统配置文件或关键应用日志内容（支持行数限制） | Windows / Linux | 只读自动放行 |
| `run_script` | 受限执行内置在 `scripts/` 或 Skill 包中的专用诊断脚本 | Windows / Linux | 需用户确认 |
| `get_machine_history` | 查询当前主机的历史故障画像、排查档案与过往案例记录 | 通用 | 只读自动放行 |
| `write_report` | 将最终排查结论与修复建议生成 Markdown 格式报告至 `workspace/` | 通用 | 自动写入沙箱 |

## 📂 项目结构

```text
U-IT-Agent/
├── 启动.bat                 # Windows 一键启动脚本
├── start.sh                 # Linux 启动脚本
├── README.md               # 项目使用与架构文档
├── requirements.txt        # Python 依赖包列表
├── .env.example            # 环境变量配置模板
├── .gitignore              # Git 忽略规则
├── python/                 # (可选) U 盘便携版 Python 目录 (含全部依赖)
├── agent/                  # Agent 核心实现
│   ├── config.py           # 配置加载与安全关键词白名单/黑名单
│   ├── llm.py              # OpenAI API 客户端 & Tool Calling 轮次控制 Loop
│   ├── main.py             # CLI REPL 交互入口与快捷指令解析
│   ├── memory.py           # 机器档案与知识库存储管理
│   ├── skills.py           # Skill 扫描、加载与本地/Zip 安装器
│   ├── prompts/
│   │   └── system.md       # 系统 Prompt 与排查行为规范
│   └── tools/
│       ├── system.py       # 内置只读系统诊断工具集 (进程/服务/磁盘/网络/蓝屏崩溃/BitLocker)
│       └── shell.py        # 持久化 PowerShell 会话管道 / Bash / 脚本执行器
├── skills/                 # 可扩展 Skill 技能包目录
│   └── _example-network-diag/
│       └── SKILL.md        # 示例网络诊断 Skill 包
├── scripts/                # 全局预置 PowerShell 诊断脚本目录
│   ├── check_net.ps1       # Windows 网络深入排查脚本
│   └── check_net.sh        # Linux 网络深入排查脚本
├── memory/                 # 长期记忆与经验存储
│   ├── machines/           # 主机档案
│   ├── knowledge/          # 沉淀的 Markdown 经验知识库
│   └── episodes/           # 历史排查案例 JSON
├── workspace/              # 报告与临时输出区 (Markdown 诊断报告)
└── logs/                   # 日志目录
```

---

## 🚀 快速开始

### 1. 便捷使用方式

#### 方式一：直接下载开箱即用便携版 (推荐，免安装任何环境)
- 在 [GitHub Releases](https://github.com/dustyfastest14/U-IT-Agent/releases/latest) 下载最新发布的 **`U-IT-Agent-Portable-v1.0.zip`** (约 20 MB)。
- 解压到 U 盘或电脑任意目录即可，里面已预先内置了绿色 Python 3.11 与全部依赖库。

#### 方式二：克隆源码使用系统 Python
- 目标电脑已安装 Python 3.10+ 环境。
- 安装依赖并运行：
  ```powershell
  pip install -r requirements.txt
  python agent/main.py
  ```

---

### 2. 配置 API 密钥

复制项目根目录下的 `.env.example` 并重命名为 `.env`：

```ini
API_BASE=https://api.openai.com/v1
API_KEY=your_actual_api_key_here
MODEL=gpt-4o
CONFIRM_MODE=true
```

> **注意**：若运行在内网环境且 API 接口需要代理访问，可确保本机相关 HTTP/HTTPS 代理配置正常。

---

### 3. 运行 Agent

Windows 可双击根目录下的 **`启动.bat`**；Linux 先执行 `chmod +x start.sh scripts/check_net.sh`，再运行 `./start.sh`。也可直接在命令行中运行：

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

1. **高危命令拦截**：内置 Windows 与 Linux 高危命令过滤规则（如 `format`、`rmdir /s /q c:`、`rm -rf /`、`mkfs` 等），强行拦截破坏性命令。
2. **读写分离与沙箱**：诊断输出报告与临时文件强制限定写入至 `workspace/` 路径下。
3. **交互确认**：当开启 `CONFIRM_MODE=true` 时，任何执行脚本或修改命令必须显示完整命令并得到用户明确输入的 `y` 方可运行。

---

## 📝 版本更新历史 (Changelog)

### v1.3.1 (2026-10-15)
- **Windows 控制台全链路 UTF-8 自适应**：修复在默认 CP936 (GBK) 命令行下流式输出 Emoji 及完成标识时触发 `UnicodeEncodeError` 导致闪退的缺陷；`启动.bat` 增加 `chcp 65001` 与 `PYTHONIOENCODING=utf-8`，Python 入口主动重配置流编码并提升字符兼容性。
- **Tool Calling Schema 描述补全**：修复 `get_bsod_crashes` 与 `get_bitlocker_status` 工具描述在部分环境因字符集问题丢失为问号的缺陷，确保大模型准确识别工具能力与参数。
- **PowerShell 持久会话死锁与输出防护**：将常驻会话的 `stderr` 管道合并至 `stdout`，防止大量错误输出填满 Windows 管道缓冲区引发进程挂起超时；增加原生控制台命令标准输出捕获支持。
- **字符编码与 BOM 清理**：清除系统提示词与工具实现文件中的 UTF-8 BOM (Byte Order Mark, `0xEF 0xBB 0xBF`)，保证跨平台解析一致性。

### v1.3.0 (2026-10-13)
- **持久化 PowerShell 会话管道**：引入常驻管道机制，支持跨命令变量与环境保留，大幅降低启动开销并提供超时中断自愈能力。
- **专精运维诊断工具集**：
  - 新增 `get_bsod_crashes`：蓝屏堆栈、Kernel-Power 41 异常关机及 BugCheck 停机码自动中文解码。
  - 新增 `get_bitlocker_status`：免提权检测全盘加密状态、算法与保护配置。
- **工具清单与文档结构升级**：新增内置 12 项 Tool Calling 详细参数参考表与最新架构树。

### v1.2.0 (2026-09-02)
- **Linux 跨平台运维支持**：支持 Bash 管道执行、systemd/journalctl 日志排查与硬件信息采集；增加 `start.sh` 一键启动脚本。

---

## 📄 开源许可

本项目遵循 MIT 许可证。
