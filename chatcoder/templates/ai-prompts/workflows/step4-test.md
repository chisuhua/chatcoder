# 🧪 测试阶段

{{ context_snapshot }}

## 📝 功能需求
{{ description }}

## 📌 实现依据
{% if previous_task %}
- **基于实现任务**: `{{ previous_task.task_id }}`
- **实现摘要**: {{ previous_task.description }}
{% else %}
- 无前序实现，需基于需求自行推导测试范围。
{% endif %}

## 🎯 测试目标
请生成以下内容：
1. **单元测试**  
   - 覆盖核心逻辑
   - 包含正常路径与边界条件
   - 使用项目当前测试框架（如 pytest、unittest、Jest 等）

2. **集成测试（如适用）**  
   - 验证模块间交互
   - 模拟外部依赖

3. **测试说明**  
   - 测试覆盖的关键场景
   - Mock 策略（如使用）

## 📋 输出要求
- 按文件组织，使用代码块
- 标注测试文件路径
- 保持测试风格与项目一致
- 不输出重复或冗余测试

### 📋 单元测试格式示例
{% if test_runner == "pytest" %}
```python
# 使用 pytest 风格
# 示例：
# def test_my_function():
#     assert my_function("hello") == {"result": "hello"}
```
{% elif test_runner == "unittest" %}
```python
# 使用 unittest 风格
# 示例：
# class TestMyFunction(unittest.TestCase):
#     def test_basic(self):
#         self.assertEqual(my_function("hello"), {"result": "hello"})
```
{% elif test_runner == "gtest" %}
```cpp
// 使用 Google Test
// 示例：
// TEST(MyFunctionTest, Basic) {
//   EXPECT_EQ(MyFunction("hello"), "hello");
// }
```
{% else %}
# 请使用 {{ test_runner }} 编写测试
```
{% endif %}

## 🚫 禁止行为
- 不得修改生产代码
- 不得跳过异常路径测试
- 不得生成无法通过的测试

