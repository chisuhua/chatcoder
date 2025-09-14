# chatflow/core/schema.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union

@dataclass
class ConditionTerm:
    field: str
    operator: str  # "=", "!=", ">", "<", ">=", "<="
    value: Any

@dataclass
class ConditionExpression:
    operator: str  # "and", "or", "not"
    # 使用字符串注解 'ConditionTerm' 和 'ConditionExpression' 来避免循环导入问题
    # 并使用 Union 来表示 operands 可以是这两种类型
    operands: List[Union['ConditionTerm', 'ConditionExpression']]

# 为类型检查器提供前向引用支持 (如果需要)
# ConditionExpression.update_forward_refs() # 如果使用 pydantic 则需要，dataclass 不需要

@dataclass
class PhaseDefinition:
    name: str
    task: str
    # 允许初始化时传入字典或 None
    condition: Optional[Union[Dict[str, Any], ConditionExpression]] = None
    fallback_phase: Optional[str] = None
    execution_strategy: str = "sequential"

    def __post_init__(self):
        """在 dataclass 初始化后处理 condition 字段的转换。"""
        if isinstance(self.condition, dict):
            # 递归函数：将 condition 字典转换为 ConditionExpression 对象
            def dict_to_condition_expression(cond_dict: Dict) -> ConditionExpression:
                if not isinstance(cond_dict, dict):
                    return cond_dict  # 安全检查

                operator = cond_dict.get('operator')
                if not operator:
                    # 可以选择抛出异常或用默认值处理
                    # raise ValueError("Condition dictionary must have an 'operator' key")
                    # 例如，忽略无效的 condition
                    return None 

                operands_data = cond_dict.get('operands', [])
                converted_operands = []
                for op_data in operands_data:
                    if isinstance(op_data, dict):
                        # 尝试判断是 ConditionTerm 还是嵌套的 ConditionExpression
                        if 'field' in op_data and 'operator' in op_data and 'value' in op_data:
                            # 看起来像 ConditionTerm
                            converted_operands.append(ConditionTerm(**op_data))
                        elif 'operator' in op_data: # 看起来像嵌套的 ConditionExpression
                            converted_operands.append(dict_to_condition_expression(op_data))
                        else:
                            # 无法识别，保留原样或根据策略处理
                            # converted_operands.append(op_data)
                            # 或者忽略
                            pass
                    else:
                        # 不是字典（可能是已转换的对象），保留原样
                        converted_operands.append(op_data)

                return ConditionExpression(operator=operator, operands=converted_operands)

            # 执行转换
            self.condition = dict_to_condition_expression(self.condition)
        # 如果 self.condition 已经是 ConditionExpression, None, 或转换失败，则无需处理
        # 可以添加类型检查以确保最终类型正确
        if self.condition is not None and not isinstance(self.condition, ConditionExpression):
             # 如果转换后仍不是期望的类型，可以选择设置为 None 或抛出错误
             # 例如，设置为 None 以容忍无效输入
             self.condition = None
             # 或者抛出错误
             # raise TypeError(f"Condition must be a ConditionExpression or None, got {type(self.condition)} after processing")


@dataclass
class WorkflowSchema:
    name: str
    version: str
    # 允许初始化时 phases 中包含字典或 PhaseDefinition 对象
    phases: List[Union[Dict[str, Any], PhaseDefinition]]
    
    def __post_init__(self):
        """在 dataclass 初始化后处理 phases 字段的转换。"""
        converted_phases = []
        for phase_item in self.phases:
            if isinstance(phase_item, dict):
                # 如果是字典，转换为 PhaseDefinition 对象
                # PhaseDefinition 的 __post_init__ 会处理其内部的 condition
                converted_phases.append(PhaseDefinition(**phase_item))
            elif isinstance(phase_item, PhaseDefinition):
                # 如果已经是对象，则直接添加
                # 注意：其内部的 condition 应该在它自己的 __post_init__ 中已处理
                converted_phases.append(phase_item)
            else:
                # 类型错误，可以选择跳过或抛出异常
                # raise TypeError(f"Phase item must be a dict or PhaseDefinition, got {type(phase_item)}")
                # 例如，跳过无效项
                pass
        self.phases = converted_phases # 替换为转换后的列表

    def validate(self):
        # 检查phase名称唯一性
        # 现在 self.phases 应该都是 PhaseDefinition 对象了
        if self.phases: # 确保 phases 不为空再访问
            names = [p.name for p in self.phases if hasattr(p, 'name')] # 额外安全检查
            if len(names) != len(set(names)):
                raise ValueError(f"Duplicate phase names in schema {self.name}@{self.version}")
        # 可添加更多静态检查...
