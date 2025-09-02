# 🤖 ChatCoder

> AI-Native Development Assistant —— 以 **上下文完整性** 和 **逻辑一致性** 为核心的 AI 编程协作协议引擎。

## 🚀 简介

ChatCoder 不是一个自动化工具，而是一个 **人类主导的 AI 协作流程系统**。  
它通过 **分层提问 + 摘要确认 + 状态追踪**，确保每一次 AI 协作都可信、可验证、可追溯。

## 📦 安装

```bash
pip install -e .
```

## 🧰 快速开始

```bash
# 1. 初始化项目
chatcoder init

# 2. 编辑上下文
vim PROJECT_CONTEXT.md

# 3. 生成结构化 prompt
chatcoder prompt feature-step1 "添加用户登录"

# 4. 将输出粘贴到 AI 对话窗口
# 5. 将 AI 回答摘要后确认
chatcoder confirm auth-design-v1
```

## 📂 目录结构

- `ai-prompts/`：内置的 AI 协作协议模板
- `.chatcoder/`：运行时状态与确认记录
- `PROJECT_CONTEXT.md`：项目上下文快照

---

## 🎯 核心理念

- ✅ **人类是决策者**
- ✅ **AI 是协作者**
- ✅ **ChatCoder 是协议引擎**



## 🚀 下一步（第 1 周）预告

下周我们将实现：

1. ✅ `ai-prompts/` 模板系统的复制逻辑
2. ✅ `PROJECT_CONTEXT.md` 的生成
3. ✅ `chatcoder init` 命令
4. ✅ `core/context.py` 的上下文解析

