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


### ✅ 模板设计原则总结

| 模板 | 核心目标 | 通用性保障 |
|------|----------|-----------|
| `step1-analyze` | 需求澄清与边界定义 | 不假设技术栈 |
| `step2-design` | 架构与接口设计 | 不强制语言语法 |
| `step3-implement` | 代码生成 | 仅输出变更 |
| `step4-test` | 测试覆盖 | 适配主流测试框架 |
| `step5-summary` | 变更归档 | 支持人工审查 |

chatcoder/
├── core/
│   ├── prompt.py          ← 当前文件
│   ├── context.py         ← 提供 generate_context_snapshot()
│   └── ...
├── ai-prompts/
│   └── workflows/
│       ├── step-analyze.md
│       ├── step-design.md
│       ├── step-implement.md  ← 支持 {{ project_language }} 条件渲染
│       ├── step-test.md       ← 支持 {{ test_runner }} 条件渲染
│       └── step-summary.md
└── utils/console.py       ← 提供 console 输出


## ChatContext

接口与模型定义: 这些文件共同定义了 chatcontext 库的核心契约：
models.py 定义了数据如何在组件间流动 (ContextRequest, ProvidedContext) 以及上下文的分类 (ContextType)。
provider.py 定义了 IContextProvider 接口，任何具体的上下文来源（如文件扫描器、RAG 检索器、LLM 摘要器）都需要实现它。
manager.py 定义了 IContextManager 接口，它是外部（如 chatcoder 或 chatflow）获取最终上下文的入口，并负责协调和整合来自不同 Provider 的 ProvidedContext。
