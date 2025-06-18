# 编译器前端：从代码到AST

## 第一个例子：把代码中的数字10改成42

### 概述

这是一个三步走的经典流程：**解析 -> 转换 -> 生成**。

---

### 第一步：解析 (Parsing) - 把代码文本变成AST

```python
import ast

# 你的源代码，此时它只是一个普通的字符串
source_code = """
def my_func(x):
    result = x + 10
    return result
"""

# 【关键】ast.parse() 把字符串转变成了AST对象
tree = ast.parse(source_code)
```

`ast.parse()` 是第一步，也是最重要的一步。它扮演了一个迷你“编译器前端”的角色，将你的Python代码字符串读取进去，然后构建出一个内存中的树形对象。这棵树的每一个节点都代表了你代码中的一个语法结构（比如函数定义、赋值、加法运算等）。

### 第二步：审视 (Inspection) - 查看AST的结构

```python
# ast.dump() 将这棵树的结构清晰地打印出来
print(ast.dump(tree, indent=4))
```

这行代码的输出让你能“亲眼看到”代码的骨架。让我们把输出和原始代码对应起来看：

**输出结果解读：**

```
Module(  # 整个文件是一个模块 (Module)
    body=[ # 模块的主体内容
        FunctionDef( # 这是一个函数定义 (def my_func...)
            name='my_func', # 函数名叫 my_func
            args=arguments(args=[arg(arg='x')]), # 参数是 x
            body=[ # 函数体内部
                Assign( # 这是一个赋值语句 (result = ...)
                    targets=[Name(id='result', ...)], # 赋值目标是变量'result'
                    value=BinOp( # 赋的值是一个二元运算 (x + 10)
                        left=Name(id='x', ...), # 左边是变量'x'
                        op=Add(), # 操作是“加法”
                        right=Constant(value=10) # 右边是常量 10
                    )
                ),
                Return( # 这是一个返回语句 (return result)
                    value=Name(id='result', ...) # 返回的值是变量'result'
                )
            ]
        )
    ]
)
```

通过这个输出，你可以清晰地看到，`result = x + 10` 这行简单的代码，在AST里被精确地表示为一个“赋值”节点，它的“值”又是一个“二元操作”节点，该节点下面又挂着左操作数、操作符和右操作数。**这种表示是无歧义的、结构化的**，比简单的文本查找和替换要强大得多。

### 第三步：转换 (Transformation) - 修改AST

这是整个流程中最有创造力的一步。我们通过写一个“访问者”来遍历并修改这棵树。

```python
# 定义一个转换器，它继承自 ast.NodeTransformer
class ChangeNumbersTo42(ast.NodeTransformer):
    # 这个方法的名字是固定的：visit_节点类型
    # 当遍历器遇到 Constant 节点时，就会自动调用这个方法
    def visit_Constant(self, node):
        # 检查这个常量的类型是不是数字
        if isinstance(node.value, int) or isinstance(node.value, float):
            # 【核心】返回一个全新的 Constant 节点，值为42
            # 这个新节点会替换掉原来树中的旧节点
            return ast.Constant(value=42)
        # 如果不是数字（比如字符串常量），则不作修改，返回原节点
        return node
```

* `ast.NodeTransformer` 是一个非常有用的基类，它能让你轻松地实现“查找并替换”AST节点的功能。
* 你只需要为你关心的节点类型（这里是 `Constant`，代表常量）实现对应的 `visit_Constant` 方法。
* 在这个方法里，你返回一个新的节点，`NodeTransformer`就会自动用你的新节点替换掉它正在访问的旧节点。在这里，它把代表 `10` 的那个 `Constant` 节点，换成了一个代表 `42` 的新 `Constant` 节点。

### 第四步：生成 (Unparsing) - 把修改后的AST变回代码

```python
transformer = ChangeNumbersTo42()
new_tree = transformer.visit(tree) # 对整棵树应用我们的转换规则
ast.fix_missing_locations(new_tree) # 一个辅助函数，用于更新新节点的位置信息

# 【关键】ast.unparse() 是 ast.parse() 的逆过程
new_code = ast.unparse(new_tree)
print("--- Transformed Code ---")
print(new_code)
```

`ast.unparse()` 遍历修改后的 `new_tree`，然后根据这棵树的结构，生成符合Python语法的代码字符串。因为我们之前已经把树中代表`10`的节点换成了`42`，所以生成的新代码自然就变成了 `result = x + 42`。
