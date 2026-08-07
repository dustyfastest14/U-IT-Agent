# U-IT-Agent (Windows 诊断 Agent)

U 盘双击即用的 Windows 系统/软件故障诊断与修复 Agent。

## 快速开始

1. 复制 .env.example 为 .env 并填写 API 配置：
   `ini
   API_BASE=https://api.openai.com/v1
   API_KEY=your_key_here
   MODEL=gpt-4o
   CONFIRM_MODE=true
   ``n2. 双击 启动.bat 或在命令行运行 python agent/main.py`n
