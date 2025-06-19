# 导入抽象语法树（AST）模块和类型字典工具
import ast
from typing import TypedDict

# 1. 准备一段包含“危险”调用的源代码（未做异常处理的函数调用）
SOURCE_CODE = """
import json
import requests

def parse_user_data(raw_json: str) -> dict | None:
    # 危险调用：直接使用 json.loads 但未捕获 JSONDecodeError
    user_data = json.loads(raw_json)
    print("JSON parsed successfully!")
    return user_data

def fetch_website_content(url: str) -> str | None:
    # 危险调用：直接使用 requests.get 但未捕获 RequestException
    response = requests.get(url, timeout=5)
    
    # 非危险调用（无需包裹 try...except）：检查响应状态码
    response.raise_for_status()
    
    return response.text
"""


# 使用 TypedDict 定义危险调用配置的精确类型结构（约束配置字典的键和值类型）
class RiskyCallConfig(TypedDict):
    """定义危险函数调用的配置结构：
    - exception: 该调用需要捕获的异常类（字符串形式，如 "json.JSONDecodeError"）
    - fallback_return: 异常发生时的回退返回值（AST 表达式节点，如 ast.Constant(value=None)）
    """

    exception: str
    fallback_return: ast.expr  # fallback_return 必须是一个表达式节点


# 2. 定义代码加固转换器（核心类，通过 AST 操作自动增强代码健壮性）
class RobustnessEnhancer(ast.NodeTransformer):
    """自动为危险函数调用包裹 try...except 异常处理块的转换器。
    工作原理：遍历 AST 节点，识别预定义的危险调用（如 json.loads、requests.get），
            并为其生成对应的 try...except 结构，实现自动异常捕获和错误处理。
    """

    # 预定义的危险调用及其配置（键为函数名，值为 RiskyCallConfig 类型）
    RISKY_CALLS: dict[str, RiskyCallConfig] = {
        "json.loads": {
            "exception": "json.JSONDecodeError",  # 需要捕获的异常类
            "fallback_return": ast.Constant(
                value=None
            ),  # 异常时返回 None
        },
        "requests.get": {
            "exception": "requests.RequestException",  # 需要捕获的异常类
            "fallback_return": ast.Constant(
                value=None
            ),  # 异常时返回 None
        },
    }

    def _is_risky_call(self, node: ast.AST) -> str | None:
        """检查一个 AST 节点是否是预定义的危险调用。
        Args:
            node: 待检查的 AST 节点
        Returns:
            危险调用名称（如 "json.loads"）或 None（非危险调用）
        """
        # 仅处理函数调用节点（ast.Call 类型）
        if not isinstance(node, ast.Call):
            return None

        # 提取函数名（如 json.loads、requests.get）
        func_name = ast.unparse(node.func)

        # 检查是否在预定义的危险调用列表中
        if func_name in self.RISKY_CALLS:
            return func_name
        return None

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """访问赋值语句节点（如 user_data = json.loads(...)），为危险调用添加异常处理。
        Args:
            node: 赋值语句的 AST 节点
        Returns:
            可能修改后的 AST 节点（包裹 try...except 块）或原节点
        """
        # 检查赋值的右值是否是危险调用
        risky_call_name = self._is_risky_call(node.value)
        if not risky_call_name:
            return node  # 非危险调用，直接返回原节点

        # 获取该危险调用的配置（异常类和回退值）
        config = self.RISKY_CALLS[risky_call_name]
        exception_name = config["exception"]

        # 仅处理简单赋值（如 a = ...，而非 a.b = ... 或 (a, b) = ...）
        if len(node.targets) == 1 and isinstance(
            node.targets[0], ast.Name
        ):
            pass  # 符合条件，继续处理
        else:
            return node  # 复杂赋值，跳过处理

        # 构建 except 块：捕获异常并打印错误信息，设置回退值
        except_handler = ast.ExceptHandler(
            type=ast.parse(
                exception_name, mode="eval"
            ).body,  # 解析异常类为 AST 节点
            name="e",  # 异常变量名
            body=[
                # 打印错误信息（如 "Error in json.loads: 解码失败"）
                ast.Expr(
                    value=ast.Call(
                        func=ast.Name(
                            id="print", ctx=ast.Load()
                        ),  # 调用 print 函数
                        args=[
                            # 格式化字符串（f"Error in {risky_call_name}: {e}"）
                            ast.JoinedStr(
                                values=[
                                    ast.Constant(
                                        value=f"Error in {risky_call_name}: "
                                    ),
                                    ast.FormattedValue(
                                        value=ast.Name(
                                            id="e", ctx=ast.Load()
                                        ),  # 异常对象 e
                                        conversion=-1,  # 不转换格式（默认 str(e)）
                                    ),
                                ]
                            )
                        ],
                        keywords=[],
                    )
                ),
                # 将回退值赋给原变量（如 user_data = None）
                ast.Assign(
                    targets=node.targets,
                    value=config["fallback_return"],
                ),
            ],
        )

        # 将原赋值语句包裹在 try 块中，返回完整的 try...except 结构
        return ast.Try(
            body=[node],
            handlers=[except_handler],
            orelse=[],
            finalbody=[],
        )

    def visit_Expr(self, node: ast.Expr) -> ast.AST:
        """访问表达式语句节点（如 requests.get(...)），为危险调用添加异常处理。
        Args:
            node: 表达式语句的 AST 节点
        Returns:
            可能修改后的 AST 节点（包裹 try...except 块）或原节点
        """
        # 检查表达式内容是否是危险调用
        risky_call_name = self._is_risky_call(node.value)
        if not risky_call_name:
            return node  # 非危险调用，直接返回原节点

        # 获取该危险调用的配置（异常类）
        config = self.RISKY_CALLS[risky_call_name]
        exception_name = config["exception"]

        # 构建 except 块：捕获异常并打印错误信息
        except_handler = ast.ExceptHandler(
            type=ast.parse(
                exception_name, mode="eval"
            ).body,  # 解析异常类为 AST 节点
            name="e",  # 异常变量名
            body=[
                # 打印错误信息（如 "Error in requests.get: 连接超时"）
                ast.Expr(
                    value=ast.Call(
                        func=ast.Name(
                            id="print", ctx=ast.Load()
                        ),  # 调用 print 函数
                        args=[
                            # 格式化字符串（f"Error in {risky_call_name}: {e}"）
                            ast.JoinedStr(
                                values=[
                                    ast.Constant(
                                        value=f"Error in {risky_call_name}: "
                                    ),
                                    ast.FormattedValue(
                                        value=ast.Name(
                                            id="e", ctx=ast.Load()
                                        ),  # 异常对象 e
                                        conversion=-1,  # 不转换格式（默认 str(e)）
                                    ),
                                ]
                            )
                        ],
                        keywords=[],
                    )
                ),
            ],
        )

        # 将原表达式语句包裹在 try 块中，返回完整的 try...except 结构
        return ast.Try(
            body=[node],
            handlers=[except_handler],
            orelse=[],
            finalbody=[],
        )


# --- 执行流程 ---
# 解析原始代码为 AST 树
tree = ast.parse(SOURCE_CODE)
# 初始化代码加固转换器
enhancer = RobustnessEnhancer()
# 遍历 AST 并应用转换（自动添加 try...except 块）
new_tree = enhancer.visit(tree)
# 修复 AST 节点缺失的位置信息（确保生成代码的行号、列号正确）
ast.fix_missing_locations(new_tree)

# 输出原始代码和加固后的代码对比
print("------ 原始代码 ------")
print(SOURCE_CODE)
print("\n------ 加固后的代码 ------")
print(ast.unparse(new_tree))  # 将 AST 转换回可读的 Python 代码
