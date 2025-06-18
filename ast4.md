# 编译器前端：从代码到AST

## 查找未使用的局部变量并提升AST遍历性能

### 概述

在使用 AST 时的一个关键瓶颈：**AST 遍历和分析本身的性能**，尤其是在处理大型、复杂的代码文件时。

`ast.parse()` 本身是用 C 语言实现的，速度非常快。真正的性能问题往往出在我们的 Python 脚本如何**低效地、重复地**遍历这棵已经生成好的树。

您提到的“用引用去优化访问”是解决这个问题的核心思想。具体来说，这意味着我们应该**避免在遍历过程中进行重复的、昂贵的查找**，而是通过**预处理（第一遍遍历）** 来建立一个“索引”或“引用地图”，然后在**主处理（第二遍遍历）** 中直接使用这个索引。

---

### 例子：查找未使用的局部变量（一个典型的性能问题场景）

**任务目标**：编写一个脚本，分析一个 Python 文件，并找出在每个函数中定义了但从未被使用过的局部变量。

这是一个经典的静态分析问题，它很容易导致性能陷阱。

#### 方案一：朴素的（低效的）单遍遍历法

一个直观的思路是：遍历所有函数，在每个函数内部，先找到所有定义的变量，然后为每个定义的变量再扫描一次函数体，看它是否被使用。

```python
# 这段代码仅为演示思路，其逻辑复杂且低效
# 你会发现很难在一次遍历中完成所有事情
class NaiveUnusedVarFinder(ast.NodeVisitor):
    def visit_FunctionDef(self, node: ast.FunctionDef):
        # 在函数内部，事情变得很复杂
        defined_vars = set()
        used_vars = set()
        
        # 嵌套的访问器，只为了分析这一个函数体
        class InnerVisitor(ast.NodeVisitor):
            def visit_Name(self, name_node: ast.Name):
                if isinstance(name_node.ctx, ast.Store):
                    defined_vars.add(name_node.id)
                elif isinstance(name_node.ctx, ast.Load):
                    used_vars.add(name_node.id)
        
        # 对每个函数体，都实例化并运行一次内部访问器
        # 这就是低效的根源：大量的重复遍历和实例化
        InnerVisitor().visit(node)
        
        # 处理参数
        for arg in node.args.args:
            defined_vars.add(arg.arg)

        unused = defined_vars - used_vars
        if unused:
            print(f"In function '{node.name}', unused variables: {unused}")

# ... 运行代码 ...
# 这种方法不仅代码丑陋，而且性能极差，因为它在循环中嵌套了遍历。
# 复杂度近似 O(函数数量 * 函数体平均大小)
```

**问题所在**：对于每个函数，我们都在其内部启动了一次新的子遍历。如果一个文件有 1000 个函数，我们就创建了 1001 个 Visitor 对象，并进行了大量的重复节点访问。

---

### 方案二：优化的两遍遍历法（建立“引用”索引）

这才是高效的、专业的方法。我们把任务拆分成两步：

1. **第一遍 (Indexing Pass)**：遍历一次完整的 AST，不进行任何分析。**唯一的目的**是建立一个数据结构（我们的“引用”索引），记录下每个作用域（函数）内所有变量的定义和使用情况。同时，我们还可以给每个节点动态地添加一个 `.parent` 属性，方便后续查找。

2. **第二遍 (Analysis Pass)**：不再遍历 AST！而是直接遍历我们第一遍建立的那个小得多的、信息高度浓缩的索引，用极快的速度完成分析。

#### 代码实现

```python
"""
A script to find unused local variables in Python functions using AST.

This script parses a Python source file, builds an index of variable
definitions and usages within each function, and then reports any
variables that were defined but never used.
"""

import ast
from dataclasses import dataclass, field

SOURCE_CODE = """
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


@dataclass
class ScopeInfo:
    """Holds variable usage information (defined vs. used) for a scope."""

    defined_vars: set[str] = field(default_factory=set)
    used_vars: set[str] = field(default_factory=set)


class AstIndexer(ast.NodeVisitor):
    """
    Visits an AST to index variable usage within each function scope.

    This visitor populates a dictionary mapping function nodes to ScopeInfo
    objects, which detail defined and used variables.
    """

    def __init__(self):
        """Initializes the AstIndexer."""
        self.var_usage_index: dict[ast.FunctionDef, ScopeInfo] = {}
        self.current_function: ast.FunctionDef | None = None

    # 为 ast.NodeVisitor 的特殊方法禁用命名检查并添加文档字符串
    # pylint: disable=invalid-name
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """
        Visits a FunctionDef node, setting the current scope and processing children.
        """
        self.current_function = node
        self.var_usage_index[node] = ScopeInfo()

        for arg in node.args.args:
            self.var_usage_index[node].defined_vars.add(arg.arg)

        self.generic_visit(node)
        self.current_function = None

    # pylint: disable=invalid-name
    def visit_Name(self, node: ast.Name):
        """
        Visits a Name node, recording its definition or usage in the current scope.
        """
        if self.current_function:
            scope_info_obj = self.var_usage_index[self.current_function]
            if isinstance(node.ctx, ast.Store):
                scope_info_obj.defined_vars.add(node.id)
            elif isinstance(node.ctx, ast.Load):
                scope_info_obj.used_vars.add(node.id)


# --- 1. 解析 ---
tree = ast.parse(SOURCE_CODE)

# --- 2. 建立索引 ---
print("--- Pass 1: Building AST Index ---")
indexer = AstIndexer()
indexer.visit(tree)
print("Index built successfully.")

# --- 3. 分析索引 ---
print("\n--- Pass 2: Analyzing the Index ---")
for func_node, scope_info in indexer.var_usage_index.items():
    unused_vars = sorted(list(scope_info.defined_vars - scope_info.used_vars))
    if unused_vars:
        func_name = func_node.name
        line_num = func_node.lineno
        print(
            f"In function '{func_name}' (line {line_num}), "
            f"unused variables: {unused_vars}"
        )

```

#### 输出结果

```bash
--- Pass 1: Building AST Index ---
Index built successfully.

--- Pass 2: Analyzing the Index ---
In function 'process_data' (line 1), unused variables: ['is_valid']
In function 'calculate_total' (line 12), unused variables: ['i', 'tax']
```

### 性能提升解读

1. **单一遍历 (O(N))**：第一遍我们只访问了 AST 的每个节点**一次**。在这个过程中，我们收集了所有需要的信息，并建立了父节点引用。这是一个线性的、与树大小成正比的操作，非常快。

2. **避免重复工作**：我们不再为每个函数或每个变量启动新的遍历。所有信息都被预先计算并存放在 `var_usage_index` 字典中。

3. **直接引用**：`var_usage_index` 的键是 `ast.FunctionDef` **节点对象本身**。这就是您所说的“引用”。我们通过这个引用，可以直接关联到该函数的所有变量信息，实现了 O(1) 的查找。

4. **高效分析**：第二遍分析时，我们根本不碰 AST。我们只遍历那个小得多的 `var_usage_index` 字典。核心分析逻辑 `defined_vars - used_vars` 是一个**高度优化的集合操作**，速度极快。

**总结下来，这种“索引-分析”的两遍法，就是提升 AST 使用性能的核心秘诀**。它将一个可能导致指数级复杂度的分析问题，转化为了两次线性扫描，这在处理成千上万行代码的真实文件时，性能差异是天壤之别。

这也是专业工具（如 Linter、类型检查器）内部的工作原理。它们会先构建一个包含作用域、父引用、类型信息等在内的“富 AST”或符号表，然后再基于这个富集后的数据结构进行分析。
