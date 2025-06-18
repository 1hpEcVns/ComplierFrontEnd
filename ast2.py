import ast
import inspect

# 1. 准备一段带有类型注解和文档字符串的源代码
source_code = """
import datetime

class User:
    pass

def get_user_by_id(user_id: int, active_only: bool = True) -> User | None:
    \"\"\"
    根据用户ID查找用户。

    这是一个功能强大的函数，可以从数据库或缓存中检索用户信息。
    如果用户不存在，则返回 None。
    \"\"\"
    # 实际的数据库查询逻辑...
    if user_id == 1:
        return User()
    return None

def calculate_age(birth_date: datetime.date) -> int:
    \"\"\"计算用户的当前年龄。\"\"\"
    today = datetime.date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age
"""


# 2. 这次我们用 NodeVisitor，因为它只分析、不修改 AST
class MarkdownGenerator(ast.NodeVisitor):
    """
    一个遍历AST的访问者，它会收集函数信息并构建Markdown文本。
    """

    def __init__(self):
        self.markdown_lines = ["# Python Code Documentation\n"]

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # --- 2.1. 提取函数签名 ---
        # ast.unparse() 是一个新且强大的工具，可以直接将AST节点转回代码字符串
        signature = ast.unparse(node)
        # unparse 会把整个函数都转出来，我们只取 def 开头到冒号的部分
        signature_line = signature.splitlines()[0].strip().replace(":", "")

        self.markdown_lines.append(f"## Function: `{node.name}`\n")
        self.markdown_lines.append("**Signature:**")
        self.markdown_lines.append(f"```python\n{signature_line}\n```\n")

        # --- 2.2. 提取文档字符串 ---
        # ast.get_docstring() 是获取文档字符串最安全、最标准的方法
        docstring = ast.get_docstring(node)
        if docstring:
            self.markdown_lines.append("**Description:**")
            # inspect.cleandoc 可以很好地处理多行docstring的缩进问题
            self.markdown_lines.append(f"{inspect.cleandoc(docstring)}\n")

        # 让访问器继续深入遍历函数的子节点（虽然这里我们不需要）
        self.generic_visit(node)

    def get_markdown(self) -> str:
        return "\n".join(self.markdown_lines)


# 3. 执行“解析 -> 分析 -> 生成文档”的流程
tree = ast.parse(source_code)

generator = MarkdownGenerator()
generator.visit(tree)  # 开始遍历AST
markdown_output = generator.get_markdown()

print("------ Generated Markdown ------")
print(markdown_output)
