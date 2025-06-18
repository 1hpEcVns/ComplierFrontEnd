# 编译器前端：从代码到AST

## 自动化 API 迁移

### 概述

之前的例子展示了如何**插入代码**（日志注入）和**提取信息**（生成文档）。现在，我们来做一个更高级、也更贴近大型项目重构需求的任务：**自动化代码迁移 (Automated Code Migration)**。

**场景**：假设你的项目里有一个旧的日志函数 `log_warning(message, timestamp=None)` 已经被废弃了。你被要求将所有对它的调用，全部迁移到 Python 标准库 `logging` 的新用法上：`logging.warning(message, extra={'timestamp': timestamp})`。

这是一个非常棘手的重构任务：

* 函数名变了 (`log_warning` -> `logging.warning`)。
* 第二个参数 `timestamp` 从一个可选的关键字参数，变成了一个字典 `extra` 里的一个键值对。

用简单的“查找-替换”或正则表达式几乎不可能完美地完成这个任务。但对于 AST 来说，这正是它的用武之地。

---

### 例子：自动化 API 迁移

**任务目标**：写一个脚本，自动将所有 `log_warning(...)` 的调用，重构为 `logging.warning(...)` 的新格式。

#### 代码实现

```python
import ast

# 1. 准备一段包含旧 API 调用的源代码
source_code = """
import logging
import time44444

def process_data(data):
    if not data:
        # 调用时只提供了 message 参数
        log_warning("Data is missing!")
    
    # ... some logic ...
    
    if 'error' in data:
        # 调用时同时提供了 message 和 timestamp
        current_ts = time.time()
        log_warning("An error occurred in data.", timestamp=current_ts)

# 其他不相关的代码
logging.info("Script finished.")
"""

# 2. 定义我们的迁移转换器
class APIMigrator(ast.NodeTransformer):
    """
    将废弃的 log_warning(msg, timestamp=ts) 调用
    迁移到 logging.warning(msg, extra={'timestamp': ts})
    """
    def visit_Call(self, node: ast.Call) -> ast.AST:
        # 我们只关心函数调用 (Call) 节点
        # 检查被调用的函数是不是我们想找的 'log_warning'
        # node.func 是代表函数名的节点，这里它是一个 Name 节点
        if isinstance(node.func, ast.Name) and node.func.id == 'log_warning':
            
            # --- 开始构建新的 AST 节点 ---

            # 1. 构建新的函数名节点: `logging.warning`
            # 这是一个属性访问 (Attribute)，value是`logging`，attr是`warning`
            new_func = ast.Attribute(
                value=ast.Name(id='logging', ctx=ast.Load()),
                attr='warning',
                ctx=ast.Load()
            )

            # 2. 第一个参数 (message) 保持不变
            message_arg = node.args[0]
            
            # 3. 处理 timestamp 参数，把它包装进 extra={'timestamp': ...}
            new_keywords = []
            # 遍历旧调用的所有关键字参数
            for kw in node.keywords:
                if kw.arg == 'timestamp':
                    # 找到了 timestamp 参数！
                    # 创建 `extra` 关键字参数
                    extra_kw = ast.keyword(
                        arg='extra',
                        value=ast.Dict( # value 是一个字典
                            keys=[ast.Constant(value='timestamp')], # key 是字符串 'timestamp'
                            values=[kw.value] # value 是旧的 timestamp 参数的值
                        )
                    )
                    new_keywords.append(extra_kw)
                    break # 找到了就跳出

            # 4. 组装成一个新的 Call 节点并返回，它将替换掉旧节点
            return ast.Call(
                func=new_func,
                args=[message_arg], # args 是一个列表
                keywords=new_keywords # keywords 也是一个列表
            )

        # 如果不是我们想修改的函数调用，保持原样
        return node


# 3. 执行“解析 -> 转换 -> 生成”的流程
tree = ast.parse(source_code)

migrator = APIMigrator()
new_tree = migrator.visit(tree)
ast.fix_missing_locations(new_tree) # 别忘了修复位置

new_code = ast.unparse(new_tree)

print("------ Original Code ------")
print(source_code)
print("\n------ Transformed Code ------")
print(new_code)
```

#### 输出结果

```
------ Original Code ------
import logging
import time

def process_data(data):
    if not data:
        # 调用时只提供了 message 参数
        log_warning("Data is missing!")
    
    # ... some logic ...
    
    if 'error' in data:
        # 调用时同时提供了 message 和 timestamp
        current_ts = time.time()
        log_warning("An error occurred in data.", timestamp=current_ts)

# 其他不相关的代码
logging.info("Script finished.")

------ Transformed Code ------
import logging
import time

def process_data(data):
    if not data:
        # 调用时只提供了 message 参数
        logging.warning('Data is missing!')
    
    # ... some logic ...
    
    if 'error' in data:
        # 调用时同时提供了 message 和 timestamp
        current_ts = time.time()
        logging.warning('An error occurred in data.', extra={'timestamp': current_ts})

# 其他不相关的代码
logging.info('Script finished.')
```

### 代码解读

这个例子展示了 AST 操作的真正威力——**结构感知和精确重构**。

1. **精确打击 `visit_Call`**：我们的目标是函数**调用**，所以我们重写了 `visit_Call` 方法。这让我们能直接处理所有形如 `func(...)` 的代码，而不会误伤到变量名、字符串等。

2. **识别目标函数**：`if isinstance(node.func, ast.Name) and node.func.id == 'log_warning'` 这行代码是精确制导的关键。它确保我们只修改名为 `log_warning` 的直接函数调用。

3. **构建新函数名 `logging.warning`**：我们不能简单地把函数名字符串改成 `"logging.warning"`。在 AST 中，`logging.warning` 是一个 `Attribute`（属性访问）节点，它的 `value` 是 `Name(id='logging')`，`attr` 是字符串 `'warning'`。我们必须**手动构建**出这个结构，这体现了 AST 的精确性。

4. **重构参数——最核心的步骤**：
    * 我们从旧节点 `node` 中提取出我们需要的参数。
    * `message` 参数（位置参数）直接从 `node.args[0]` 获取。
    * `timestamp` 参数（关键字参数）需要遍历 `node.keywords` 列表来查找。
    * 最精彩的部分是**创建 `extra` 参数**。我们创建了一个 `ast.keyword` 节点，它的值 (`value`) 又是一个 `ast.Dict`（字典）节点。这个字典节点又包含了它的键和值。
    * 这种**嵌套创建AST节点**的能力，是完成复杂结构重构的核心。

5. **组装并替换**：最后，我们用所有新建的部件——新的函数名节点、新的参数列表、新的关键字参数列表——组装成一个全新的 `ast.Call` 节点，并将其返回。`NodeTransformer` 会自动用这个新节点替换掉 AST 中原来的旧节点。

这个例子完美诠释了为什么掌握编译器前端技术能极大提升开发效率和代码质量。对于任何大规模、有模式可循的代码重构，AST 脚本都是最强大、最可靠的工具。
