# 📌 上下文提取规则

请按以下格式填写 `PROJECT_CONTEXT.md`，以便 ChatCoder 自动解析：

## 🏗️ 基本信息
- 项目名称: {{name}}
- 项目类型: {{Web API | Library | CLI | Service}}
- 主要语言: {{Python | C++ | ...}}

## 📁 目录结构
- 源码目录: {{src/}}
- 测试目录: {{tests/}}
- 配置目录: {{config/}}

## 🧩 命名规范
- Python 文件: {{snake_case}}
- Python 类: {{PascalCase}}
- C++ 头文件: {{MyClass.h}}
- 函数: {{snake_case}}

## 🛠️ 工具链
- 构建: {{pip | CMake | make}}
- 测试: {{pytest | gtest}}
- 格式化: {{black | clang-format}}

## 🔐 安全原则
- {{输入必须验证}}
- {{敏感操作需日志}}
