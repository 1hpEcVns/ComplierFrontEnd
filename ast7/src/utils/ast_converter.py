"""
AST与字典相互转换工具
"""

import ast
from typing import Dict, List, Any, Union


def ast_to_dict(node: ast.AST) -> Union[dict, list, str]:
    """将AST节点转换为字典格式"""
    if not isinstance(node, ast.AST):
        return node

    node_type = node.__class__.__name__
    result = {"node_type": node_type}

    # 添加行列号信息，对于调试非常有用
    if hasattr(node, "lineno"):
        result["lineno"] = node.lineno
    if hasattr(node, "col_offset"):
        result["col_offset"] = node.col_offset

    for field in node._fields:
        value = getattr(node, field)
        if isinstance(value, list):
            result[field] = [ast_to_dict(item) for item in value]
        else:
            result[field] = ast_to_dict(value)

    return result


def dict_to_ast(d: Union[dict, list, str]) -> Union[ast.AST, list, str]:
    """将字典格式转换回AST节点"""
    if isinstance(d, list):
        return [dict_to_ast(item) for item in d]
    if not isinstance(d, dict) or "node_type" not in d:
        return d

    # 创建字典副本以避免修改原始数据
    d_copy = d.copy()
    node_type = d_copy.pop("node_type")

    # 从标准 ast 模块中找到对应的节点类
    NodeClass = getattr(ast, node_type)

    # 保存行号信息
    lineno = d_copy.pop("lineno", None)
    col_offset = d_copy.pop("col_offset", None)

    # 递归转换所有子字段
    for key, value in d_copy.items():
        d_copy[key] = dict_to_ast(value)

    # 实例化节点类
    node = NodeClass(**d_copy)

    # 重新设置行号信息
    if lineno is not None:
        node.lineno = lineno
    if col_offset is not None:
        node.col_offset = col_offset

    return node


def parse_code_to_ast(code: str) -> Dict[str, Any]:
    """解析Python代码为AST字典格式"""
    try:
        tree = ast.parse(code)
        return ast_to_dict(tree)
    except SyntaxError as e:
        raise ValueError(f"语法错误: {e}")
    except Exception as e:
        raise ValueError(f"解析错误: {e}")


def ast_to_code(ast_dict: Dict[str, Any]) -> str:
    """将AST字典转换回Python代码"""
    try:
        ast_node = dict_to_ast(ast_dict)
        return ast.unparse(ast_node)
    except Exception as e:
        raise ValueError(f"代码生成错误: {e}")
