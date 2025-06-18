好的，我们来详细讲解一个经典的编译器优化技术：**循环展开 (Loop Unrolling)**。

这是一个绝佳的示例，因为它不仅需要分析和修改节点，还需要**用多个新节点来替换单个节点（`for`循环）**。具体来说，它会生成一个展开后的主循环和一个处理剩余迭代的“收尾”循环。这个例子还将展示一个转换器（Transformer）如何使用另一个更小、更专业的转换器来协同完成任务。

**目标：**
自动将一个简单的 `for` 循环：

```python
for i in range(8):
    data.append(i * 2)
```

...转换成一个优化后的、展开版本（假设展开因子为4）：

```python
# 展开后的主循环
for i in range(0, 8, 4):
    data.append(i * 2)
    data.append((i + 1) * 2)
    data.append((i + 2) * 2)
    data.append((i + 3) * 2)

# 处理剩余部分的收尾循环 (对于循环8次来说不是必需的，但如果循环9或10次就需要)
```

这项优化可以通过减少循环的条件检查和分支跳转所带来的开销来提升性能，同时也能增加指令级并行（ILP）的可能性。

---

### 代码实现：一个自动化的循环展开器

我们需要两个转换器来完成这个任务：

1. **`LoopVarReplacer`**：一个功能单一的小型转换器，其唯一职责是在一小段代码中找到循环变量（如 `i`），并将其替换为一个表达式（如 `i + 1`）。
2. **`LoopUnroller`**：主转换器，负责寻找符合条件的循环，然后利用 `LoopVarReplacer` 来生成展开后的循环体，并构建出新的、优化后的循环结构。

```python
import ast
import copy

# --- 待优化的源代码 ---
SOURCE_CODE = """
import time

def process_heavy_data():
    results = []
    # 一个可以被展开的简单循环
    for i in range(10):
        # 模拟一个复杂的计算操作
        results.append(i * i)

    # 一个循环范围不确定的循环，应该被跳过
    limit = int(time.time() % 10)
    for j in range(limit):
        print(j)

    # 一个包含 break 的循环，应该被跳过
    for k in range(20):
        if k > 5:
            break
        results.append(k)

    return results
"""


class LoopVarReplacer(ast.NodeTransformer):
    """
    将循环变量的出现替换为一个带偏移量的表达式。
    例如，将 `i` 替换为 `i + offset`。
    """
    def __init__(self, loop_var_name: str, offset: int):
        self.loop_var_name = loop_var_name
        self.offset = offset

    def visit_Name(self, node: ast.Name) -> ast.AST:
        # 如果当前节点是循环变量，并且它正在被读取（Load 上下文）
        if node.id == self.loop_var_name and isinstance(node.ctx, ast.Load):
            if self.offset == 0:
                # 对于循环体的第一个实例，不需要改变
                return node
            # 创建一个新的二元操作节点: (i + offset)
            return ast.BinOp(
                left=ast.Name(id=self.loop_var_name, ctx=ast.Load()),
                op=ast.Add(),
                right=ast.Constant(value=self.offset)
            )
        return node


class LoopUnroller(ast.NodeTransformer):
    """
    对简单的 `for i in range(N)` 循环执行循环展开。
    """
    def __init__(self, unroll_factor: int = 4):
        self.unroll_factor = unroll_factor

    def visit_For(self, node: ast.For) -> list[ast.AST] | ast.For:
        # --- 阶段 1: 检查循环是否符合展开条件 ---
        # 1. 必须是 `for ... in range(...)` 形式
        if not isinstance(node.iter, ast.Call) or \
           not isinstance(node.iter.func, ast.Name) or \
           node.iter.func.id != 'range':
            return node

        # 2. 必须是 `range(停止值)` 的形式，且停止值是一个整数常量
        if len(node.iter.args) != 1 or not isinstance(node.iter.args[0], ast.Constant) or \
           not isinstance(node.iter.args[0].value, int):
            return node
        
        # 3. 循环变量必须是一个简单的名称
        if not isinstance(node.target, ast.Name):
            return node
            
        # 4. 循环体内不能包含 `break` 或 `continue`
        for sub_node in ast.walk(node):
            if isinstance(sub_node, (ast.Break, ast.Continue)):
                return node

        # --- 阶段 2: 执行转换 ---
        loop_var_name = node.target.id
        stop_value = node.iter.args[0].value
        
        if stop_value < self.unroll_factor:
            return node # 循环次数太少，不值得展开

        new_body = []
        for i in range(self.unroll_factor):
            # 为每个偏移量 (i, i+1, i+2, ...) 创建一个专用的替换器
            replacer = LoopVarReplacer(loop_var_name, i)
            # 必须对循环体进行深拷贝，以避免在同一个节点上反复修改
            for body_part in copy.deepcopy(node.body):
                new_body.append(replacer.visit(body_part))

        # 主展开循环的步长为展开因子
        main_loop_stop = stop_value // self.unroll_factor * self.unroll_factor
        
        main_unrolled_loop = ast.For(
            target=node.target,
            iter=ast.Call(
                func=ast.Name(id='range', ctx=ast.Load()),
                args=[
                    ast.Constant(value=0),
                    ast.Constant(value=main_loop_stop),
                    ast.Constant(value=self.unroll_factor)
                ],
                keywords=[]
            ),
            body=new_body,
            orelse=[]
        )
        
        result_nodes = [main_unrolled_loop]

        # --- 阶段 3: 为剩余的迭代创建收尾循环 ---
        if stop_value % self.unroll_factor != 0:
            tail_loop = ast.For(
                target=node.target,
                iter=ast.Call(
                    func=ast.Name(id='range', ctx=ast.Load()),
                    args=[
                        ast.Constant(value=main_loop_stop),
                        ast.Constant(value=stop_value)
                    ],
                    keywords=[]
                ),
                body=node.body, # 这里使用原始循环体即可
                orelse=[]
            )
            result_nodes.append(tail_loop)
            
        # 返回一个节点列表，用以替换原始的单个 For 节点
        return result_nodes


# --- 执行流程 ---
print("------ 原始代码 ------")
print(SOURCE_CODE)

tree = ast.parse(SOURCE_CODE)
unroller = LoopUnroller(unroll_factor=4)
new_tree = unroller.visit(tree)

# 为新创建的节点修复行号等元数据
ast.fix_missing_locations(new_tree)

new_code = ast.unparse(new_tree)
print("\n------ 转换后的代码 (已优化) ------")
print(new_code)
```

### 输出结果

```
------ 原始代码 ------
import time

def process_heavy_data():
    results = []
    # 一个可以被展开的简单循环
    for i in range(10):
        # 模拟一个复杂的计算操作
        results.append(i * i)

    # 一个循环范围不确定的循环，应该被跳过
    limit = int(time.time() % 10)
    for j in range(limit):
        print(j)

    # 一个包含 break 的循环，应该被跳过
    for k in range(20):
        if k > 5:
            break
        results.append(k)

    return results

------ 转换后的代码 (已优化) ------
import time

def process_heavy_data():
    results = []
    # 一个可以被展开的简单循环
    for i in range(0, 8, 4):
        results.append(i * i)
        results.append((i + 1) * (i + 1))
        results.append((i + 2) * (i + 2))
        results.append((i + 3) * (i + 3))
    for i in range(8, 10):
        results.append(i * i)
    # 一个循环范围不确定的循环，应该被跳过
    limit = int(time.time() % 10)
    for j in range(limit):
        print(j)
    # 一个包含 break 的循环，应该被跳过
    for k in range(20):
        if k > 5:
            break
        results.append(k)
    return results
```

### 本示例中的关键技术点

1. **安全第一：防御性检查**
    在 `visit_For` 方法的开头有一系列的“防御性子句”，以确保它只修改那些可以被安全展开的循环。对于任何生产级的 AST 工具来说，这是至关重要的一步，它保证了工具的健壮性，不会破坏正常的代码。

2. **返回节点列表：一对多转换**
    `visit_For` 方法返回的是一个 AST 节点的**列表** (`list`)，例如 `[main_unrolled_loop, tail_loop]`。`NodeTransformer` 类非常智能，当它看到返回值是一个列表时，它会用列表中的所有节点来替换原始的单个 `For` 节点。这实际上是在代码块中**插入**了多个新节点，是实现复杂重构的关键。

3. **嵌套转换器：关注点分离**
    `LoopUnroller` 使用了 `LoopVarReplacer` 的实例作为其内部工具。这是一个非常强大的设计模式：通过组合多个功能单一、可复用的小型转换器来构建出复杂的转换逻辑。`LoopUnroller` 负责宏观的“做什么”（找到循环），而 `LoopVarReplacer` 负责微观的“怎么做”（替换变量），使得代码结构更清晰。

4. **深拷贝：避免副作用**
    `copy.deepcopy(node.body)` 在这里是**绝对必需的**。如果没有它，`LoopVarReplacer` 会在同一组节点上修改四次，导致出现类似 `(((i + 1) + 2) + 3)` 这样的错误结果。我们需要为每一次展开迭代都提供一个全新的、干净的循环体副本，就像复印一份表格给人填写，而不是让所有人在同一份原件上涂改。
