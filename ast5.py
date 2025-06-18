"""使用AST（抽象语法树）实现自动循环展开优化。"""

import ast
import copy

SOURCE_CODE = """
def process_heavy_data():
    results = []
    # 可以被展开的简单循环
    for i in range(10):
        results.append(i * i)
    # 包含 break 的循环，应该被跳过
    for k in range(20):
        if k > 5:
            break
        results.append(k)
"""


class LoopVarReplacer(ast.NodeTransformer):
    """将循环变量替换为一个带偏移量的符号表达式 (i -> i + 1)。"""

    def __init__(self, var_name: str, offset: int):
        self.var_name = var_name
        self.offset = offset

    # pylint: disable=invalid-name
    def visit_Name(self, node: ast.Name) -> ast.AST:
        """访问名称节点，如果是循环变量则进行替换。"""
        if node.id == self.var_name and isinstance(node.ctx, ast.Load):
            if self.offset == 0:
                return node
            return ast.BinOp(
                left=ast.Name(id=self.var_name, ctx=ast.Load()),
                op=ast.Add(),
                right=ast.Constant(value=self.offset),
            )
        return node


class ConstantVarReplacer(ast.NodeTransformer):
    """将循环变量替换为一个具体的常量值 (i -> 8)。"""

    def __init__(self, var_name: str, value: int):
        self.var_name = var_name
        self.value = value

    # pylint: disable=invalid-name
    def visit_Name(self, node: ast.Name) -> ast.AST:
        """访问名称节点，如果是循环变量则替换为常量。"""
        if node.id == self.var_name and isinstance(node.ctx, ast.Load):
            return ast.Constant(value=self.value)
        return node


class LoopUnroller(ast.NodeTransformer):
    """对简单的 `for i in range(N)` 循环执行完全展开优化。"""

    def __init__(self, unroll_factor: int = 4):
        self.unroll_factor = unroll_factor

    # pylint: disable=invalid-name
    def visit_For(self, node: ast.For) -> list[ast.AST] | ast.For:
        """访问For循环节点，如果符合条件则进行展开。"""
        # --- 阶段 1: 依次进行类型安全的检查 ---
        if not isinstance(node.target, ast.Name):
            return node
        iter_node = node.iter
        if not isinstance(iter_node, ast.Call):
            return node
        func_node = iter_node.func
        if not (isinstance(func_node, ast.Name) and func_node.id == "range"):
            return node
        if len(iter_node.args) != 1:
            return node
        stop_node = iter_node.args[0]
        # 【修复】将过长的行拆分
        if not (
            isinstance(stop_node, ast.Constant) and isinstance(stop_node.value, int)
        ):
            return node
        # 【修复】将过长的行拆分
        if any(isinstance(n, (ast.Break, ast.Continue)) for n in ast.walk(node)):
            return node

        # --- 阶段 2: 执行转换 ---
        loop_var, stop_val = node.target.id, stop_node.value
        if stop_val < self.unroll_factor:
            return node

        result_nodes: list[ast.AST] = []
        main_loop_stop = (stop_val // self.unroll_factor) * self.unroll_factor

        if main_loop_stop > 0:
            unrolled_body = []
            for i in range(self.unroll_factor):
                loop_replacer = LoopVarReplacer(loop_var, i)
                for part in copy.deepcopy(node.body):
                    unrolled_body.append(loop_replacer.visit(part))
            main_loop = ast.For(
                target=node.target,
                iter=ast.Call(
                    func=ast.Name(id="range", ctx=ast.Load()),
                    args=[
                        ast.Constant(0),
                        ast.Constant(main_loop_stop),
                        ast.Constant(self.unroll_factor),
                    ],
                    keywords=[],
                ),
                body=unrolled_body,
                orelse=[],
            )
            result_nodes.append(main_loop)

        for i in range(main_loop_stop, stop_val):
            const_replacer = ConstantVarReplacer(loop_var, i)
            for part in copy.deepcopy(node.body):
                result_nodes.append(const_replacer.visit(part))

        return result_nodes if result_nodes else node


# --- 执行流程 ---
tree = ast.parse(SOURCE_CODE)
unroller = LoopUnroller(unroll_factor=4)
new_tree = unroller.visit(tree)
ast.fix_missing_locations(new_tree)

print("------ 优化后的代码 ------")
print(ast.unparse(new_tree))
