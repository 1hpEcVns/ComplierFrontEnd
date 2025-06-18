import ast
from dataclasses import dataclass, field

# 1. 准备一段代码来分析 (保持不变)
source_code = """
def process_data(data, config):
    # 'config' is used
    if config.get('debug'):
        print("Processing...")
    
    # 'is_valid' is defined but never used
    is_valid = True
    
    # 'result' is defined and used
    result = len(data)
    return result

def calculate_total(items):
    # 'total' is defined and used
    total = 0
    # 'i' is defined (in comprehension) but only used inside it
    # 'item_price' is defined and used
    prices = [item_price for i, item_price in enumerate(items)]
    
    # 'tax' is defined but never used
    tax = 0.1
    
    for p in prices:
        total += p
    return total
"""


# 定义我们索引的数据结构 (保持不变)
@dataclass
class ScopeInfo:
    defined_vars: set[str] = field(default_factory=set)
    used_vars: set[str] = field(default_factory=set)


# 2. 重构后的 AstIndexer 类 (核心变化在此)
class AstIndexer(ast.NodeVisitor):
    """
    通过一次遍历来索引每个函数作用域中变量的定义和使用情况。
    """

    def __init__(self):
        # 我们的核心索引：{ 函数节点 -> ScopeInfo }
        self.var_usage_index: dict[ast.FunctionDef, ScopeInfo] = {}
        # current_function 作为状态，在遍历时跟踪当前所在的函数作用域
        self.current_function: ast.FunctionDef | None = None

    # 注意：我们删除了之前有问题的、自定义的 visit 方法。
    # ast.NodeVisitor 的默认遍历机制会以深度优先的顺序正确地访问所有节点。

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # 步骤 1: 进入一个新的函数作用域
        self.current_function = node
        self.var_usage_index[node] = ScopeInfo()

        # 步骤 2: 将函数参数视为“已定义”的变量
        for arg in node.args.args:
            self.var_usage_index[node].defined_vars.add(arg.arg)

        # 步骤 3: 深入遍历函数体内的所有子节点
        # 当遍历到子节点时（如 Name 节点），visit_Name 方法会使用
        # self.current_function 这个我们刚设置好的状态。
        self.generic_visit(node)

        # 步骤 4: 退出当前函数作用域，防止影响其他函数的分析
        self.current_function = None

    def visit_Name(self, node: ast.Name):
        # 只处理在函数作用域内部的变量
        if self.current_function:
            scope_info = self.var_usage_index[self.current_function]
            if isinstance(node.ctx, ast.Store):
                # 'Store' 上下文意味着变量被赋值（定义）
                scope_info.defined_vars.add(node.id)
            elif isinstance(node.ctx, ast.Load):
                # 'Load' 上下文意味着变量被读取（使用）
                scope_info.used_vars.add(node.id)

        # 对于 Name 节点，不需要再深入遍历，所以我们不在这里调用 generic_visit


# 3. 执行流程 (保持不变)

# 解析AST
tree = ast.parse(source_code)

# --- 第一遍：建立索引 ---
print("--- Pass 1: Building AST Index ---")
indexer = AstIndexer()
indexer.visit(tree)
print("Index built successfully.")
# 至此，所有需要的信息都已在 indexer.var_usage_index 中

# --- 第二遍：分析索引 ---
print("\n--- Pass 2: Analyzing the Index ---")
for func_node, scope_info in indexer.var_usage_index.items():
    # 使用超高速的集合运算
    unused_vars = scope_info.defined_vars - scope_info.used_vars
    if unused_vars:
        print(
            f"In function '{func_node.name}' (line {func_node.lineno}), unused variables: {sorted(list(unused_vars))}"
        )
