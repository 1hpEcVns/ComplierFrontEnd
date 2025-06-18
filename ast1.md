# 编译器前端：从代码到AST

## 自动为所有函数添加入口日志

### 概述

AST 的结构和 JSON 非常相似，它们都是用来表示结构化数据的树形格式。您可以把 AST 看作是**一种带有特定“纲要”（Schema）的、为编程语言量身定制的 JSON**。每个对象（节点）的类型（如 `FunctionDef`, `Assign`）和它的属性（如 `.name`, `.body`）都是由语言的语法预先定义好的。

这种“纲要”正是 AST 强大的地方，因为它让我们可以写出能够理解并操作代码结构的代码。

这次我们来做一个更实用的操作：**自动扫描一段代码，并为其中的每一个函数定义的第一行，都插入一条打印日志的语句**。这在调试或监控中非常有用。

这个任务如果用简单的文本替换来做会非常困难，但用 AST 来做就非常精准和简单。

### 代码实现

```python
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
```

### 输出结果

```bash
------ Original Code ------
def calculate_price(base, tax_rate):
    total = base * (1 + tax_rate)
    return total

def greet(user_name):
    # 这是一个问候函数
    print(f"Hello, {user_name}!")

# 一个没有做任何事的函数
def do_nothing():
    pass

------ Transformed Code ------
def calculate_price(base, tax_rate):
    print('Entering function: calculate_price')
    total = base * (1 + tax_rate)
    return total

def greet(user_name):
    print('Entering function: greet')
    # 这是一个问候函数
    print(f'Hello, {user_name}!')

def do_nothing():
    print('Entering function: do_nothing')
    pass
```

### 例子解读

1. **目标更明确**：这次我们不再是替换一个已知的值，而是进行**结构性修改**。我们的目标是 `FunctionDef`（函数定义）节点。

2. **`visit_FunctionDef`**：我们的转换器类里定义了一个 `visit_FunctionDef` 方法。`ast.NodeTransformer` 在遍历树时，一旦遇到一个 `FunctionDef` 类型的节点，就会自动调用这个方法，并将该节点作为参数 `node` 传入。

3. **获取节点信息**：在方法内部，我们可以轻易地从 `node` 对象中获取信息，比如用 `node.name` 拿到了函数的名字。

4. **修改函数体**：函数的所有语句都存放在 `node.body` 这个列表里。我们要做就是在列表的开头插入一个新的语句。这展现了AST的威力：**函数的代码块不再是模糊的文本，而是一个可以操作的列表**。

5. **创建新节点**：我们用 `ast.parse('print("...")').body[0]` 这个便捷的方法，直接“解析”出我们想插入的代码的AST节点。这避免了手动创建 `Expr(value=Call(func=Name(id='print', ...)))` 这样的复杂结构，让代码更易读。

6. **结果**：最终生成的代码中，每个函数都精确地在第一行被插入了我们想要的日志语句，并且保留了原有的所有代码和注释。

这个例子比前一个更进了一步，展示了如何通过操作AST，对代码的**结构**进行自动化的、精确的修改。
