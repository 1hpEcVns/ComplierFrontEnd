# 从代码到AST

## 自动化代码加固：为危险调用自动包裹 try...except

在大型软件项目中，确保代码的健壮性至关重要。一个常见的疏忽是开发者忘记为可能失败的操作（如网络请求、文件解析）添加异常处理，这可能导致整个应用程序崩溃。本教程将通过一个高级示例，展示如何使用AST技术，编写一个脚本来自动扫描代码库，并为预定义的“危险”函数调用包裹上 `try...except` 块，从而实现自动化代码加固。

### 任务目标

我们的目标是编写一个脚本，能将下面这段脆弱的代码：

#### 【原始代码】

```python
import json
import requests

def parse_user_data(raw_json: str):
    # 危险：未处理 json.loads 可能抛出的异常
    user_data = json.loads(raw_json)
    return user_data

def fetch_website_content(url: str):
    # 危险：未处理 requests.get 可能抛出的异常
    response = requests.get(url)
    return response.text
```

...自动转换为下面这段健壮的代码：

#### 【加固后的代码】

```python
import json
import requests

def parse_user_data(raw_json: str):
    try:
        user_data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f'Error in json.loads: {e}')
        user_data = None
    return user_data

def fetch_website_content(url: str):
    try:
        response = requests.get(url)
    except requests.RequestException as e:
        print(f'Error in requests.get: {e}')
        response = None
    return response.text
```

### 本示例的核心技术与思想

这个任务将教会我们几个关键的、超越基础操作的高级AST编程技巧：

1. **替换控制流**：学习如何用一个复杂的控制流节点 (`ast.Try`) 来替换一个简单的语句节点 (`ast.Assign` 或 `ast.Expr`)。
2. **静态类型驱动开发**：使用 `typing.TypedDict` 为配置信息定义一个精确的“类型契约”，从根源上消除静态分析错误，使代码更健壮、更易于维护。
3. **精确节点识别**：利用 `ast.unparse` 简化对复杂函数调用（如 `a.b.c()`）的识别。
4. **程序化节点构建**：学习如何像搭乐高一样，从零开始构建出包含 f-string、函数调用和赋值等逻辑的复杂 `except` 块。
5. **父节点替换原则**：理解为何要修改表达式的“父语句”而非表达式本身，这是进行结构性代码转换的核心思想。

### 完整实现（类型安全与注释增强版）

```python
# 导入抽象语法树（AST）模块和类型字典工具
import ast
from typing import TypedDict

# 1. 准备一段包含“危险”调用的源代码（未做异常处理的函数调用）
SOURCE_CODE = """
import json
import requests

def parse_user_data(raw_json: str) -> dict | None:
    # 危险调用：直接使用 json.loads 但未捕获 JSONDecodeError
    user_data = json.loads(raw_json)
    print("JSON parsed successfully!")
    return user_data

def fetch_website_content(url: str) -> str | None:
    # 危险调用：直接使用 requests.get 但未捕获 RequestException
    response = requests.get(url, timeout=5)
    
    # 非危险调用（无需包裹 try...except）：检查响应状态码
    response.raise_for_status()
    
    return response.text
"""


# 使用 TypedDict 定义危险调用配置的精确类型结构（约束配置字典的键和值类型）
class RiskyCallConfig(TypedDict):
    """定义危险函数调用的配置结构：
    - exception: 该调用需要捕获的异常类（字符串形式，如 "json.JSONDecodeError"）
    - fallback_return: 异常发生时的回退返回值（AST 表达式节点，如 ast.Constant(value=None)）
    """
    exception: str
    fallback_return: ast.expr  # fallback_return 必须是一个表达式节点


# 2. 定义代码加固转换器（核心类，通过 AST 操作自动增强代码健壮性）
class RobustnessEnhancer(ast.NodeTransformer):
    """自动为危险函数调用包裹 try...except 异常处理块的转换器。
    工作原理：遍历 AST 节点，识别预定义的危险调用（如 json.loads、requests.get），
            并为其生成对应的 try...except 结构，实现自动异常捕获和错误处理。
    """

    # 预定义的危险调用及其配置（键为函数名，值为 RiskyCallConfig 类型）
    RISKY_CALLS: dict[str, RiskyCallConfig] = {
        "json.loads": {
            "exception": "json.JSONDecodeError",  # 需要捕获的异常类
            "fallback_return": ast.Constant(value=None),  # 异常时返回 None
        },
        "requests.get": {
            "exception": "requests.RequestException",  # 需要捕获的异常类
            "fallback_return": ast.Constant(value=None),  # 异常时返回 None
        },
    }

    def _is_risky_call(self, node: ast.AST) -> str | None:
        """检查一个 AST 节点是否是预定义的危险调用。"""
        if not isinstance(node, ast.Call):
            return None
        func_name = ast.unparse(node.func)
        if func_name in self.RISKY_CALLS:
            return func_name
        return None

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """访问赋值语句节点（如 user_data = json.loads(...)），为危险调用添加异常处理。"""
        risky_call_name = self._is_risky_call(node.value)
        if not risky_call_name:
            return node

        config = self.RISKY_CALLS[risky_call_name]
        exception_name = config["exception"]

        if not (len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
            return node

        except_handler = ast.ExceptHandler(
            type=ast.parse(exception_name, mode="eval").body,
            name="e",
            body=[
                ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id="print", ctx=ast.Load()),
                        args=[
                            ast.JoinedStr(
                                values=[
                                    ast.Constant(value=f"Error in {risky_call_name}: "),
                                    ast.FormattedValue(
                                        value=ast.Name(id="e", ctx=ast.Load()),
                                        conversion=-1,
                                    ),
                                ]
                            )
                        ],
                        keywords=[],
                    )
                ),
                ast.Assign(targets=node.targets, value=config["fallback_return"]),
            ],
        )
        return ast.Try(body=[node], handlers=[except_handler], orelse=[], finalbody=[])

    def visit_Expr(self, node: ast.Expr) -> ast.AST:
        """访问表达式语句节点（如 requests.get(...)），为危险调用添加异常处理。"""
        risky_call_name = self._is_risky_call(node.value)
        if not risky_call_name:
            return node

        config = self.RISKY_CALLS[risky_call_name]
        exception_name = config["exception"]

        except_handler = ast.ExceptHandler(
            type=ast.parse(exception_name, mode="eval").body,
            name="e",
            body=[
                ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id="print", ctx=ast.Load()),
                        args=[
                            ast.JoinedStr(
                                values=[
                                    ast.Constant(value=f"Error in {risky_call_name}: "),
                                    ast.FormattedValue(
                                        value=ast.Name(id="e", ctx=ast.Load()),
                                        conversion=-1,
                                    ),
                                ]
                            )
                        ],
                        keywords=[],
                    )
                ),
            ],
        )
        return ast.Try(body=[node], handlers=[except_handler], orelse=[], finalbody=[])

# --- 执行流程 ---
tree = ast.parse(SOURCE_CODE)
enhancer = RobustnessEnhancer()
new_tree = enhancer.visit(tree)
ast.fix_missing_locations(new_tree)

print("------ 原始代码 ------")
print(SOURCE_CODE)
print("\n------ 加固后的代码 ------")
print(ast.unparse(new_tree))
```

### 关键技术点深度解析

#### 1. 类型契约：`TypedDict` 的妙用

这是本次重构最关键的一步。在早期版本中，静态分析器无法推断 `RISKY_CALLS` 字典内部的结构，导致类型错误。通过定义 `RiskyCallConfig(TypedDict)`，我们为配置项建立了一个清晰的 **“类型契约”**。这等于向Python的类型系统宣告：
> “任何符合 `RiskyCallConfig` 的字典，都必须包含一个名为 `exception` 的字符串和一个名为 `fallback_return` 的 `ast.expr` 节点。”

这不仅解决了所有类型检查错误，还使得 `RISKY_CALLS` 的结构变得**自文档化**，任何尝试添加不合规配置的开发者都会立即收到工具的提示。

#### 2. 核心思想：修改语句，而非表达式

初学者可能会尝试重写 `visit_Call` 来处理 `json.loads()`。但这是行不通的，因为一个函数调用（表达式 `expr`）不能被 `try...except`（语句 `stmt`）直接替换。
正确的做法是找到包含这个危险调用的**父语句节点**，然后用 `ast.Try` 节点替换掉整个父语句。这就是我们重写 `visit_Assign` 和 `visit_Expr` 的原因。这个**“寻找父语句”**的模式是进行结构性代码转换的通用法则。

#### 3. 蓝图式构建：`ast.Try` 和 `ast.ExceptHandler`

构建新的控制流就像根据蓝图盖房子。`ast.Try` 节点是房子的框架，它有几个关键参数：

* `body`: `try` 块的内容，是一个语句列表。我们将原始的语句 `[node]` 放入其中。
* `handlers`: `except` 块的列表。这里我们放入精心构建的 `ExceptHandler`。

而 `ast.ExceptHandler` 则是对 `except` 块的精细描述：

* `type`: 要捕获的异常。我们使用 `ast.parse(exception_name, mode='eval').body` 这个强大技巧，直接将字符串（如 `"json.JSONDecodeError"`）解析成对应的AST节点。
* `name`: 异常变量名（`"e"`）。
* `body`: `except` 块内的逻辑，也是一个语句列表。

#### 4. 精确制导：`ast.unparse` 的优雅

如何识别一个调用是 `json.loads` 而不是 `other.loads`？函数名节点可能是简单的 `ast.Name`（如 `print`），也可能是复杂的 `ast.Attribute`（如 `json.loads`）。`ast.unparse(node.func)` 提供了一个极其优雅的解决方案：无论函数名节点结构多复杂，它都能将其还原为唯一的、可比较的字符串表示，大大简化了识别逻辑。

这个例子充分展示了AST编程的深度和广度。通过掌握这些高级技巧，你不再仅仅是代码的使用者，而是成为了代码的**塑造者**，能够开发出强大的工具来自动化地提升整个代码库的质量、安全性和可维护性。
