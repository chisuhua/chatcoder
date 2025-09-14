# chatflow/utils/conditions.py
from typing import Dict, Any
from ..core.schema import ConditionExpression, ConditionTerm

def evaluate_condition(condition: ConditionExpression, context: Dict[str, Any]) -> bool:
    """递归求值条件表达式"""
    if condition.operator == "and":
        return all(_evaluate_term(term, context) for term in condition.operands)
    elif condition.operator == "or":
        return any(_evaluate_term(term, context) for term in condition.operands)
    elif condition.operator == "not":
        return not _evaluate_term(condition.operands[0], context)
    else:
        raise ValueError(f"Unknown operator: {condition.operator}")

def _evaluate_term(term: 'ConditionTerm', context: Dict[str, Any]) -> bool:
    """求值单个条件项"""
    value = _get_nested_value(term.field, context)
    
    if term.operator == "=":
        return value == term.value
    elif term.operator == "!=":
        return value != term.value
    elif term.operator == ">":
        return value > term.value
    elif term.operator == "<":
        return value < term.value
    elif term.operator == ">=":
        return value >= term.value
    elif term.operator == "<=":
        return value <= term.value
    else:
        raise ValueError(f"Unknown operator: {term.operator}")

def _get_nested_value(path: str, obj: Dict[str, Any]) -> Any:
    """支持点号嵌套访问: "code.risk_level" """
    keys = path.split('.')
    for key in keys:
        if isinstance(obj, dict) and key in obj:
            obj = obj[key]
        else:
            return None
    return obj

