# 💻 实现阶段

{{ context_snapshot }}

## 📝 功能需求
{{ description }}

## 📌 设计依据
{% if previous_task %}
- **基于设计任务**: `{{ previous_task.task_id }}`
- **设计摘要**:  
  {{ previous_task.description }}
{% else %}
- 无前序设计，需自行完成模块划分与接口定义。
{% endif %}

## 🎯 实现目标
请输出以下内容：

1. **新增或修改的文件**  
   - 每个文件单独用代码块包裹
   - 标注文件路径
   - 仅输出变更部分，非完整文件
   - 保持与项目现有风格一致

2. **关键逻辑说明**  
   - 核心算法或流程的简要注释
   - 重要决策的 rationale

## 📋 输出格式示例
### src/user_service.py
```python
def create_user(username: str) -> User:
    # 实现逻辑
    pass
```

### tests/test_user.py
```python
def test_create_user():
    # 测试逻辑
    pass
```

## 🚫 禁止行为
- 不得修改与本功能无关的代码
- 不得引入新依赖（除非已在设计阶段声明）
- 不得忽略类型检查或格式化规则
- 不得输出解释性文本（标题和注释除外）

