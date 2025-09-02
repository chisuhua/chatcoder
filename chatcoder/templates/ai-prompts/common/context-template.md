# 📂 项目上下文模板

## 🏗️ 项目基本信息
- 项目类型: {{Web API / CLI / Library / Embedded}}
- 主要语言: {{Python / C++ / ... }}
- 构建系统: {{pip / CMake }}
- 测试框架: {{pytest / Google Test / ... }}
- 代码风格: {{Black / clang-format}}

## 📂 结构原则
- 模块组织: {{功能分组 / 分层架构}}
- 目录层级: ≤ 3
- 公共接口: {{__init__.py / 头文件 / 模块}}

## 🧩 命名规范
- 文件: {{snake_case}}
- 函数: {{snake_case / camelCase}}
- 类: {{PascalCase}}
- 测试: {{test_*.py / *_test.cpp}}

## 🔐 安全要求
- 敏感操作: {{记录日志}}
- 输入: {{验证}}
- 禁止: {{goto（C++）}}

## 📚 文档约定
- 函数注释: {{Google / Doxygen}}
- 类型提示: {{必须}}
