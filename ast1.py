import ast

# 1. 准备一段包含多个函数的源代码
source_code = """
def calculate_price(base, tax_rate):
    total = base * (1 + tax_rate)
    return total

def greet(user_name):
    # 这是一个问候函数
    print(f"Hello, {user_name}!")

# 一个没有做任何事的函数
def do_nothing():
    pass
"""


# 2. 定义我们的转换器
class FunctionLoggerInjector(ast.NodeTransformer):
    """
    一个遍历AST的转换器，它会找到所有函数定义节点 (FunctionDef)，
    并在每个函数体的开头插入一个 print() 语句。
    """

    def visit_FunctionDef(self, node):
        # node 是当前访问到的函数定义节点 (FunctionDef)

        # 创建我们要插入的新节点。
        # 这里用一个小技巧：直接用 ast.parse() 来生成单个语句的AST，
        # 比手动构建 Expr -> Call -> Name -> Constant 等节点要简单得多！
        log_message = f"Entering function: {node.name}"
        # 注意 .body[0] 是因为 ast.parse() 返回一个完整的 Module，我们需要其中的第一个（也是唯一一个）语句
        new_node = ast.parse(f'print("{log_message}")').body[0]

        # 将新创建的日志节点插入到函数体(body)列表的最前面
        node.body.insert(0, new_node)

        # 修复新节点的位置信息，这是一个好习惯
        ast.fix_missing_locations(node)

        # 返回修改后的节点。因为我们是在原节点上修改，所以直接返回 node
        return node


# 3. 执行“解析 -> 转换 -> 生成”的流程
# 解析
tree = ast.parse(source_code)

# 转换
transformer = FunctionLoggerInjector()
new_tree = transformer.visit(tree)

# 生成
new_code = ast.unparse(new_tree)

print("------ Original Code ------")
print(source_code)
print("\n------ Transformed Code ------")
print(new_code)
