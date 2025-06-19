"""
AST转换服务
"""

import ast
import copy
from typing import Dict, List, Any, Union


class TransformService:
    """AST转换服务类"""

    @staticmethod
    def rename_function_in_ast(
        node: Dict[str, Any], old_name: str, new_name: str
    ) -> Dict[str, Any]:
        """重命名函数"""
        result = copy.deepcopy(node)

        def rename_recursive(n):
            if isinstance(n, dict):
                # 重命名函数定义
                if n.get("node_type") == "FunctionDef" and n.get("name") == old_name:
                    n["name"] = new_name

                # 重命名函数调用
                elif n.get("node_type") == "Call":
                    func = n.get("func")
                    if (
                        func
                        and func.get("node_type") == "Name"
                        and func.get("id") == old_name
                    ):
                        func["id"] = new_name

                # 重命名变量引用
                elif n.get("node_type") == "Name" and n.get("id") == old_name:
                    n["id"] = new_name

                # 递归处理所有子节点
                for key, value in n.items():
                    if isinstance(value, (dict, list)):
                        rename_recursive(value)

            elif isinstance(n, list):
                for item in n:
                    rename_recursive(item)

        rename_recursive(result)
        return result

    @staticmethod
    def add_logging_to_functions(
        node: Dict[str, Any], log_message: str = "Function called"
    ) -> Dict[str, Any]:
        """为函数添加日志"""
        result = copy.deepcopy(node)

        def add_log_recursive(n):
            if isinstance(n, dict):
                if n.get("node_type") == "FunctionDef":
                    func_name = n.get("name", "unknown")

                    # 创建日志语句
                    log_stmt = {
                        "node_type": "Expr",
                        "value": {
                            "node_type": "Call",
                            "func": {
                                "node_type": "Name",
                                "id": "print",
                                "ctx": {"node_type": "Load"},
                            },
                            "args": [
                                {
                                    "node_type": "Constant",
                                    "value": f"{log_message}: {func_name}",
                                }
                            ],
                            "keywords": [],
                        },
                    }

                    # 将日志语句添加到函数体开头
                    if "body" in n and isinstance(n["body"], list):
                        n["body"].insert(0, log_stmt)

                # 递归处理子节点
                for key, value in n.items():
                    if isinstance(value, (dict, list)):
                        add_log_recursive(value)

            elif isinstance(n, list):
                for item in n:
                    add_log_recursive(item)

        add_log_recursive(result)
        return result

    @staticmethod
    def replace_constants(
        node: Dict[str, Any],
        old_value: Union[str, int, float],
        new_value: Union[str, int, float],
    ) -> Dict[str, Any]:
        """替换常量值"""
        result = copy.deepcopy(node)

        def replace_recursive(n):
            if isinstance(n, dict):
                if n.get("node_type") == "Constant" and n.get("value") == old_value:
                    n["value"] = new_value

                # 递归处理子节点
                for key, value in n.items():
                    if isinstance(value, (dict, list)):
                        replace_recursive(value)

            elif isinstance(n, list):
                for item in n:
                    replace_recursive(item)

        replace_recursive(result)
        return result

    @staticmethod
    def remove_statements_by_type(
        node: Dict[str, Any], stmt_type: str
    ) -> Dict[str, Any]:
        """按类型删除语句"""
        result = copy.deepcopy(node)

        def remove_recursive(n):
            if isinstance(n, dict):
                # 处理包含语句列表的字段
                for key in ["body", "orelse", "finalbody"]:
                    if key in n and isinstance(n[key], list):
                        # 过滤掉指定类型的语句
                        n[key] = [
                            stmt
                            for stmt in n[key]
                            if not (
                                isinstance(stmt, dict)
                                and stmt.get("node_type") == stmt_type
                            )
                        ]

                        # 递归处理剩余的语句
                        for stmt in n[key]:
                            remove_recursive(stmt)

                # 递归处理其他子节点
                for key, value in n.items():
                    if key not in ["body", "orelse", "finalbody"] and isinstance(
                        value, (dict, list)
                    ):
                        remove_recursive(value)

            elif isinstance(n, list):
                for item in n:
                    remove_recursive(item)

        remove_recursive(result)
        return result

    @staticmethod
    def get_available_transforms() -> Dict[str, Dict[str, Any]]:
        """获取可用的转换操作"""
        return {
            "rename_function": {
                "name": "重命名函数",
                "description": "重命名函数定义和所有调用点",
                "parameters": [
                    {"name": "old_name", "type": "string", "description": "原函数名"},
                    {"name": "new_name", "type": "string", "description": "新函数名"},
                ],
            },
            "add_logging": {
                "name": "添加日志",
                "description": "在所有函数开头添加日志输出",
                "parameters": [
                    {
                        "name": "log_message",
                        "type": "string",
                        "description": "日志消息前缀",
                        "default": "Function called",
                    }
                ],
            },
            "replace_constants": {
                "name": "替换常量",
                "description": "查找并替换代码中的常量值",
                "parameters": [
                    {"name": "old_value", "type": "any", "description": "原常量值"},
                    {"name": "new_value", "type": "any", "description": "新常量值"},
                ],
            },
            "remove_statements": {
                "name": "删除语句",
                "description": "按类型删除特定的语句",
                "parameters": [
                    {
                        "name": "stmt_type",
                        "type": "string",
                        "description": "语句类型",
                        "options": ["Expr", "Pass", "Import", "ImportFrom"],
                    }
                ],
            },
        }
