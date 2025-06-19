# 编译器前端：从代码到 AST

## 使用AST实现自动循环展开优化

在掌握了基础的 AST 分析与修改之后，让我们挑战一个真正接近编译器底层优化的经典技术：**循环展开 (Loop Unrolling)**。

这个例子将向我们展示 AST 操作的真正威力。它不仅需要分析和修改节点，还需要**用多个新节点来替换单个节点**，并体现出编写生产级代码转换工具所需的**健壮性**和**设计模式**。

**核心目标：**
自动将一个简单的 `for` 循环：

```python
for i in range(10):
    results.append(i * i)
```

...转换成一个优化后的、展开版本（假设展开因子为 4）：

```python
# 展开后的主循环，步长为4
for i in range(0, 8, 4):
    results.append(i * i)
    results.append((i + 1) * (i + 1))
    results.append((i + 2) * (i + 2))
    results.append((i + 3) * (i + 3))

# 处理剩余迭代的“收尾”代码
results.append(8 * 8)
results.append(9 * 9)
```

这项优化能通过减少循环判断和分支跳转的次数来提升性能，并为更深层次的指令级并行优化创造条件。

---

### 代码实现：一个健壮的自动循环展开器

要优雅地实现这个功能，我们需要将复杂任务拆解。我们将设计三个独立的转换器协同工作：

1. **`LoopVarReplacer`**：一个小型工具，负责将循环变量 `i` 替换为 `i + offset` 的表达式。
2. **`ConstantVarReplacer`**：另一个小型工具，负责将循环变量 `i` 直接替换为一个具体的常量值，用于处理收尾部分。
3. **`LoopUnroller`**：主转换器，负责：
   - **检查**一个循环是否可以被安全地展开。
   - **编排**其他转换器来生成展开后的主循环和收尾代码。
   - 用**一组新节点**替换掉原始的单个 `for` 循环节点。

```python
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

    def visit_Name(self, node: ast.Name) -> ast.AST:
        """访问名称节点，如果是循环变量则替换为常量。"""
        if node.id == self.var_name and isinstance(node.ctx, ast.Load):
            return ast.Constant(value=self.value)
        return node


class LoopUnroller(ast.NodeTransformer):
    """对简单的 `for i in range(N)` 循环执行循环展开优化。"""

    def __init__(self, unroll_factor: int = 4):
        self.unroll_factor = unroll_factor

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
        if not (
            isinstance(stop_node, ast.Constant) and isinstance(stop_node.value, int)
        ):
            return node
        # 关键安全检查：遍历循环体子树，确保没有break或continue
        if any(isinstance(n, (ast.Break, ast.Continue)) for n in ast.walk(node)):
            return node

        # --- 阶段 2: 执行转换 ---
        loop_var, stop_val = node.target.id, stop_node.value
        if stop_val < self.unroll_factor:
            return node # 循环次数太少，不值得展开

        result_nodes: list[ast.AST] = []
        main_loop_stop = (stop_val // self.unroll_factor) * self.unroll_factor

        # 2.1 创建主循环
        if main_loop_stop > 0:
            unrolled_body: list[ast.stmt] = []
            for i in range(self.unroll_factor):
                loop_replacer = LoopVarReplacer(loop_var, i)
                for part in copy.deepcopy(node.body): # 必须深拷贝！
                    visited = loop_replacer.visit(part)
                    if isinstance(visited, ast.stmt):
                        unrolled_body.append(visited)
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

        # 2.2 创建收尾部分 (直接将剩余迭代展开为独立语句)
        for i in range(main_loop_stop, stop_val):
            const_replacer = ConstantVarReplacer(loop_var, i)
            for part in copy.deepcopy(node.body):
                result_nodes.append(const_replacer.visit(part))

        # 返回节点列表，用以替换原始的单个For节点
        return result_nodes if result_nodes else node


# --- 执行流程 ---
tree = ast.parse(SOURCE_CODE)
unroller = LoopUnroller(unroll_factor=4)
new_tree = unroller.visit(tree)
ast.fix_missing_locations(new_tree)

print("------ 原始代码 ------")
print(SOURCE_CODE.strip())
print("\n------ 优化后的代码 ------")
print(ast.unparse(new_tree))
```

### 输出结果

```bash

------ 原始代码 ------
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

------ 优化后的代码 ------
def process_heavy_data():
    results = []
    for i in range(0, 8, 4):
        results.append(i * i)
        results.append((i + 1) * (i + 1))
        results.append((i + 2) * (i + 2))
        results.append((i + 3) * (i + 3))
    results.append(8 * 8)
    results.append(9 * 9)
    for k in range(20):
        if k > 5:
            break
        results.append(k)

```

### 本示例中的关键技术点

1. **安全第一：防御性检查**
    在 `visit_For` 方法的开头有一系列的“防御性子句”。它严格检查循环是否为 `for i in range(常量)` 的简单形式，更重要的是，它使用 `ast.walk(node)` **遍历循环体的所有子节点**，确保其中不包含 `break` 或 `continue`。这是编写生产级代码转换工具的黄金法则：**宁可不做，不能做错**。

2. **一对多转换：返回节点列表**
    `visit_For` 方法的返回值类型是 `list[ast.AST] | ast.For`。当它决定展开循环时，它返回的是一个**节点列表**。`NodeTransformer` 非常智能，当它看到返回值是一个列表时，它会用列表中的**所有节点**来替换原始的**单个 `For` 节点**。这是实现复杂重构（如用多个语句替换一个语句）的关键特性。

3. **关注点分离：嵌套使用转换器**
    `LoopUnroller` 并没有自己处理所有替换逻辑，而是像一个总指挥，调用了 `LoopVarReplacer` 和 `ConstantVarReplacer` 这两个“专家”去完成具体任务。这是一个强大的设计模式：**通过组合多个功能单一、可复用的小型转换器来构建复杂的转换逻辑**，使代码结构更清晰，更易于维护。

4. **状态隔离：`copy.deepcopy()` 的重要性**
    代码中 `copy.deepcopy(node.body)` 的使用是**绝对必需的**。AST 节点是可变对象。如果没有深拷贝，`LoopVarReplacer` 在第一次迭代时修改了节点，第二次迭代就会在**已被修改的节点上再次修改**，导致出现 `(((i + 1) + 2) + 3)` 这样的灾难性错误。深拷贝确保了每次展开都像是在一张干净的“复印件”上操作，互不干扰。

5. **高效收尾：常量折叠的应用**
    对于剩余的几次迭代（如 `range(10)` 中的第 8 和第 9 次），脚本没有生成一个新的 `for` 循环，而是直接使用 `ConstantVarReplacer` 将循环体复制了两次，并把 `i` 直接替换成了常量 `8` 和 `9`。这本身就是一种更彻底的优化，称为**常量折叠**，它完全消除了剩余部分的循环开销。
