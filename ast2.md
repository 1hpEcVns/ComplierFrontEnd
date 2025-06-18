# 编译器前端：从代码到AST

## 另一个例子：自动为代码生成 Markdown 格式的说明文档

### 概述

**这和 Rust 的 `#[derive]` 宏在思想上是完全一致的，都是元编程（Metaprogramming）的体现**。

### AST 操作与 Rust `derive` 的深刻联系

这个相似点，揭示了编译器前端技术的核心价值：**代码即数据（Code as Data）**。

| 特性 | Python AST 脚本 (我们的例子) | Rust `#[derive(Debug)]` 宏 |
| :--- | :--- | :--- |
| **输入** | 一段作为**字符串**的 Python 源代码。 | 一个 Rust 的 `struct` 或 `enum` 的**定义**。 |
| **处理核心** | 外部脚本调用 `ast.parse()` 将代码解析成**AST**，然后遍历并操作这棵树。 | Rust 编译器在编译时，将 `struct` 的结构信息传递给 `derive` 宏。宏接收到的也是一种**类AST的结构（TokenStream）**。 |
| **操作** | 我们可以写代码**任意分析或修改**这棵树。 | `derive(Debug)` 宏内部有预先写好的逻辑，它会**根据收到的结构信息**，生成实现 `Debug` trait 所需的 `fmt` 函数代码。 |
| **输出** | 一个**新的** Python 源代码**字符串**。 | 一段**新的** Rust 代码（实现了`Debug` trait），这段代码会被无缝地插入到编译流程中，就像你手动写的一样。 |

**核心共同点**：它们都把源代码当作一种**结构化的数据**来处理，并基于这个结构**自动生成新的代码或文本**。

唯一的区别在于集成度：

* 我们的 Python 脚本是一个**外部工具**，需要我们手动运行。
* Rust 的 `derive` 宏是**语言内置的、头等公民**，由编译器在编译时自动调用，体验更无缝。

理解了这一点，您就掌握了现代编程语言一个非常强大的特性。现在，我们就用这个能力来完成一个非常实用的任务：**代码文档自动化**。

---

### 例子：自动为 Python 函数生成 Markdown 文档

**任务目标**：写一个脚本，读取一个 Python 文件，自动为其中所有函数生成一个 `.md` 格式的文档，包含函数名称、参数、返回类型以及它的文档字符串（docstring）。

#### 代码实现

```python
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
generator.visit(tree) # 开始遍历AST
markdown_output = generator.get_markdown()

print("------ Generated Markdown ------")
print(markdown_output)
```

#### 输出结果 (这就是生成的 Markdown)

```markdown
------ Generated Markdown ------
# Python Code Documentation

## Function: `get_user_by_id`

**Signature:**
```python
def get_user_by_id(user_id: int, active_only: bool = True) -> User | None
```

**Description:**
根据用户ID查找用户。

这是一个功能强大的函数，可以从数据库或缓存中检索用户信息。
如果用户不存在，则返回 None。

## Function: `calculate_age`

**Signature:**

```python
def calculate_age(birth_date: datetime.date) -> int
```

**Description:**
计算用户的当前年龄。

### 代码解读

1. **目的：分析而非转换**
    这次我们的目的不是修改代码，而是**从代码中提取信息**。因此，我们继承了 `ast.NodeVisitor`，它是一个纯粹的“访问者”，用于遍历和分析节点，而 `ast.NodeTransformer` 则用于修改节点。

2. **`visit_FunctionDef` - 信息提取的核心**
    * 我们的核心逻辑依然在 `visit_FunctionDef` 中，因为它能精确地捕获到每一个函数定义。
    * **提取签名**: 我们巧妙地使用了 `ast.unparse(node)`，它可以将一个AST节点（这里是整个函数`node`）完美地转回代码。我们只需要结果的第一行，就得到了完整的函数签名，包括参数、默认值、类型注解和返回类型注解。这比手动拼接字符串要健壮得多！
    * **提取文档字符串**: 我们使用了 `ast.get_docstring(node)`。这是Python官方推荐的方法，它能正确处理各种边缘情况，比自己去分析 `node.body` 的第一个元素要安全得多。

3. **格式化输出**
    在提取出需要的信息（函数名、签名、文档字符串）后，我们用 f-string 将它们格式化成符合 Markdown 语法的字符串，然后添加到 `self.markdown_lines` 列表中。

4. **最终结果**
    当访问者遍历完整个 AST 后，我们就得到了一个包含所有格式化好的 Markdown 文本的列表，最后用 `"\n".join()` 将它们组合成一个完整的文档。

这个例子生动地展示了，一旦你掌握了操作 AST 的能力，你就拥有了一个**通用的、强大的代码分析和生成引擎**，可以用于实现代码转换、静态分析、文档生成、Linter 开发等各种高级任务。
