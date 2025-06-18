import ast

# 一段简单的Python代码
source_code = """
def my_func(x):
    result = x + 10
    return result
"""

# 把代码字符串解析成AST
tree = ast.parse(source_code)

# 打印出这棵树的结构，你会看到FunctionDef, arguments, Assign, BinOp等节点
print(ast.dump(tree, indent=4))


class ChangeNumbersTo42(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, int) or isinstance(node.value, float):
            # 创建一个新的Constant节点，值为42
            return ast.Constant(value=42)
        return node


transformer = ChangeNumbersTo42()
new_tree = transformer.visit(tree)  # 应用转换
ast.fix_missing_locations(new_tree)  # 修复新节点的位置信息

# 将修改后的AST转回Python代码
new_code = ast.unparse(new_tree)
print("--- Original Code ---")
print(source_code)
print("--- Transformed Code ---")
print(new_code)
# 你会看到输出的函数里，10 变成了 42
