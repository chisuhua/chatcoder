{{role: engineer}}
{{context: PROJECT_CONTEXT}}

# AI 指令：添加新功能（C++）

## 🧩 功能要求
{{功能描述}}

## ✅ 实现原则
- 创建目录: `src/{{module}}/`
- 必须包含:
  - `include/{{module}}/{{Class}}.h`
  - `src/{{module}}/{{Class}}.cpp`
  - `CMakeLists.txt`（如需）
- 头文件: `#pragma once`
- RAII 管理资源
- 参数使用 `const &`

## 🧪 测试
- `tests/{{module}}_test.cpp`
- Google Test
- 覆盖边界情况

## 🚦 渐进式交付
1. 返回类设计
2. 确认后生成头文件
3. 再生成实现

{{common/self-checklist.md}}
{{common/adr-template.md}}
{{common/principles.md#人类协作接口}}
