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
    """用于循环展开优化的变量替换器：将循环变量替换为带固定偏移量的符号表达式。

    典型场景：当循环展开时（如将 `for i in range(10)` 展开为4次迭代的副本），
    每个副本的循环变量需要调整为 `i+0`, `i+1`, `i+2`, `i+3` 的形式，
    从而在保留循环变量符号的同时实现迭代逻辑的展开。
    """

    def __init__(self, var_name: str, offset: int):
        """初始化循环变量替换器。

        Args:
            var_name: 需要替换的循环变量名（如原循环中的 `i`）
            offset: 替换时的偏移量（如展开第2个副本时，offset=1，将 `i` 替换为 `i+1`）
        """
        self.var_name = var_name
        self.offset = offset

    # pylint: disable=invalid-name
    def visit_Name(self, node: ast.Name) -> ast.AST:
        """访问名称节点，根据条件替换循环变量为带偏移量的表达式。

        仅处理处于 `Load` 上下文（读取操作）的目标循环变量：
        - 若偏移量为0，直接返回原节点（避免无意义的 `i+0` 表达式）
        - 否则生成 `i + offset` 形式的二元运算表达式节点

        Args:
            node: 当前访问的名称（Name）AST节点

        Returns:
            替换后的AST节点（可能是原节点、二元运算节点或其他节点）
        """
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
    """用于循环展开优化的常量替换器：将循环变量替换为具体的整数值。

    典型场景：当循环展开后剩余无法被展开因子整除的迭代（如 `range(10)` 中最后2次迭代），
    直接将循环变量替换为具体数值（如 `i=8`、`i=9`），从而消除循环结构，实现常量折叠优化。
    """

    def __init__(self, var_name: str, value: int):
        """初始化常量替换器。

        Args:
            var_name: 需要替换的循环变量名（如原循环中的 `i`）
            value: 替换后的具体整数值（如剩余迭代中的 `8` 或 `9`）
        """
        self.var_name = var_name
        self.value = value

    # pylint: disable=invalid-name
    def visit_Name(self, node: ast.Name) -> ast.AST:
        """访问名称节点，根据条件将循环变量替换为具体常量。

        仅处理处于 `Load` 上下文（读取操作）的目标循环变量：
        - 匹配时直接返回值为 `value` 的常量节点
        - 不匹配时返回原节点（保留其他变量的原始逻辑）

        Args:
            node: 当前访问的名称（Name）AST节点

        Returns:
            替换后的AST节点（可能是常量节点或原节点）
        """
        if node.id == self.var_name and isinstance(node.ctx, ast.Load):
            return ast.Constant(value=self.value)
        return node


class LoopUnroller(ast.NodeTransformer):
    """对简单的 `for i in range(N)` 循环执行完全展开优化。"""

    def __init__(self, unroll_factor: int = 4):
        self.unroll_factor = unroll_factor

    # pylint: disable=invalid-name
    def visit_For(self, node: ast.For) -> list[ast.AST] | ast.For:
        """访问For循环节点，如果符合条件则进行展开。

        Args:
            node: 当前遍历到的For循环AST节点

        Returns:
            展开后的节点列表（或原节点如果不满足展开条件）
        """
        # --- 阶段 1: 依次进行类型安全的检查，仅处理符合要求的简单循环 ---
        # 检查循环变量是否为简单变量名（排除元组解包等复杂形式）
        if not isinstance(node.target, ast.Name):
            return node  # 非简单变量名的循环不展开

        iter_node = node.iter
        # 检查循环迭代器是否为函数调用（range是函数调用形式）
        if not isinstance(iter_node, ast.Call):
            return node  # 非函数调用的迭代器不展开

        func_node = iter_node.func
        # 检查函数调用是否为range函数（仅处理range生成的循环）
        if not (isinstance(func_node, ast.Name) and func_node.id == "range"):
            return node  # 非range的循环不展开

        # 检查range参数数量（仅处理单参数形式range(stop)）
        if len(iter_node.args) != 1:
            return node  # 多参数range不展开（如range(start, stop)）

        stop_node = iter_node.args[0]
        # 检查循环终止值是否为整数常量（确保展开次数可静态计算）
        if not (
            isinstance(stop_node, ast.Constant) and isinstance(stop_node.value, int)
        ):
            return node  # 动态终止值的循环不展开

        # 检查循环体是否包含break/continue（复杂控制流会破坏展开逻辑）
        if any(isinstance(n, (ast.Break, ast.Continue)) for n in ast.walk(node)):
            return node  # 包含中断语句的循环不展开

        # --- 阶段 2: 执行转换，将符合条件的循环展开为多个副本 ---
        loop_var, stop_val = (
            node.target.id,
            stop_node.value,
        )  # 提取循环变量名和总迭代次数
        # 若总迭代次数小于展开因子（无展开必要），直接返回原循环
        if stop_val < self.unroll_factor:
            return node

        result_nodes: list[ast.AST] = []  # 存储展开后的所有节点（主循环+剩余迭代）
        # 计算主循环的终止值（整除展开因子后取整，保证是展开因子的整数倍）
        main_loop_stop = (stop_val // self.unroll_factor) * self.unroll_factor

        # 生成展开后的主循环（处理可被展开因子整除的部分）
        if main_loop_stop > 0:
            unrolled_body: list[ast.stmt] = []  # 存储展开后的循环体语句
            # 为每个展开副本生成替换后的循环体
            for i in range(self.unroll_factor):
                # 创建循环变量替换器（将i替换为i+0, i+1, ..., i+unroll_factor-1）
                loop_replacer = LoopVarReplacer(loop_var, i)
                # 深拷贝原循环体并应用替换（避免修改原节点）
                for part in copy.deepcopy(node.body):
                    visited = loop_replacer.visit(part)  # 执行变量替换
                    if isinstance(visited, ast.stmt):  # 确保是有效语句节点
                        unrolled_body.append(visited)

            # 构建新的主循环节点（步长设置为展开因子，减少循环次数）
            main_loop = ast.For(
                target=node.target,  # 保持原循环变量名
                iter=ast.Call(
                    func=ast.Name(id="range", ctx=ast.Load()),  # range函数调用
                    args=[
                        ast.Constant(0),  # 起始值0
                        ast.Constant(main_loop_stop),  # 终止值（展开后的总次数）
                        ast.Constant(self.unroll_factor),  # 步长=展开因子
                    ],
                    keywords=[],
                ),
                body=unrolled_body,  # 展开后的循环体（包含多个副本）
                orelse=[],  # 无else子句
            )
            result_nodes.append(main_loop)  # 将主循环加入结果列表

        # 处理剩余无法被展开因子整除的迭代（直接展开为独立语句）
        for i in range(main_loop_stop, stop_val):
            # 创建常量替换器（将循环变量直接替换为具体数值i）
            const_replacer = ConstantVarReplacer(loop_var, i)
            # 深拷贝原循环体并应用替换，生成独立执行的语句
            for part in copy.deepcopy(node.body):
                result_nodes.append(const_replacer.visit(part))  # 直接添加到结果列表

        # 返回展开后的节点列表（若有展开）或原节点（无展开时）
        return result_nodes if result_nodes else node


# --- 执行流程 ---
# 将源代码字符串解析为抽象语法树（AST），后续所有操作都基于此树进行
tree = ast.parse(SOURCE_CODE)
# 创建循环展开器实例，设置展开因子为4（即每次展开4次迭代）
unroller = LoopUnroller(unroll_factor=4)
# 通过访问者模式遍历AST，应用循环展开优化，生成优化后的新AST
new_tree = unroller.visit(tree)
# 修复AST节点中缺失的位置信息（如行号、列号），确保后续代码输出的准确性
ast.fix_missing_locations(new_tree)

# 输出优化后的代码，验证展开效果
print("------ 优化后的代码 ------")
print(ast.unparse(new_tree))  # 将优化后的AST重新转换为Python代码字符串
# 输出原始代码，便于对比优化前后的差异
print("------ 原始代码 ------")
print(SOURCE_CODE.strip())  # 去除原始代码首尾的空白字符后打印
