"""
代码执行服务
"""

import io
import sys
import contextlib
from typing import Dict, Any, Tuple


class CodeExecutionService:
    """代码执行服务类"""

    @staticmethod
    def execute_code(code: str) -> Dict[str, Any]:
        """安全执行Python代码"""
        # 捕获输出
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()

        try:
            # 重定向stdout和stderr
            with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(
                error_buffer
            ):

                # 创建受限的执行环境
                safe_globals = {
                    "__builtins__": {
                        "print": print,
                        "len": len,
                        "str": str,
                        "int": int,
                        "float": float,
                        "bool": bool,
                        "list": list,
                        "dict": dict,
                        "tuple": tuple,
                        "set": set,
                        "range": range,
                        "enumerate": enumerate,
                        "zip": zip,
                        "sum": sum,
                        "max": max,
                        "min": min,
                        "abs": abs,
                        "round": round,
                        "sorted": sorted,
                        "reversed": reversed,
                    }
                }

                # 执行代码
                exec(code, safe_globals)

            # 获取输出
            stdout_output = output_buffer.getvalue()
            stderr_output = error_buffer.getvalue()

            return {
                "success": True,
                "output": stdout_output,
                "error": stderr_output if stderr_output else None,
            }

        except Exception as e:
            return {
                "success": False,
                "output": output_buffer.getvalue(),
                "error": f"执行错误: {str(e)}",
            }

        finally:
            output_buffer.close()
            error_buffer.close()

    @staticmethod
    def validate_code(code: str) -> Tuple[bool, str]:
        """验证代码语法"""
        try:
            compile(code, "<string>", "exec")
            return True, "代码语法正确"
        except SyntaxError as e:
            return False, f"语法错误: {e}"
        except Exception as e:
            return False, f"验证错误: {e}"

    @staticmethod
    def get_execution_limits() -> Dict[str, Any]:
        """获取执行限制信息"""
        return {
            "allowed_builtins": [
                "print",
                "len",
                "str",
                "int",
                "float",
                "bool",
                "list",
                "dict",
                "tuple",
                "set",
                "range",
                "enumerate",
                "zip",
                "sum",
                "max",
                "min",
                "abs",
                "round",
                "sorted",
                "reversed",
            ],
            "forbidden_operations": [
                "文件操作 (open, read, write)",
                "网络操作 (socket, urllib)",
                "系统调用 (os, sys)",
                "导入外部模块",
                "执行外部命令",
            ],
            "security_note": "代码在受限环境中执行，仅允许基本Python操作",
        }
