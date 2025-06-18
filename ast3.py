import ast

# 1. 准备一段包含旧 API 调用的源代码
source_code = """
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
        if isinstance(node.func, ast.Name) and node.func.id == "log_warning":

            # --- 开始构建新的 AST 节点 ---

            # 1. 构建新的函数名节点: `logging.warning`
            # 这是一个属性访问 (Attribute)，value是`logging`，attr是`warning`
            new_func = ast.Attribute(
                value=ast.Name(id="logging", ctx=ast.Load()),
                attr="warning",
                ctx=ast.Load(),
            )

            # 2. 第一个参数 (message) 保持不变
            message_arg = node.args[0]

            # 3. 处理 timestamp 参数，把它包装进 extra={'timestamp': ...}
            new_keywords = []
            # 遍历旧调用的所有关键字参数
            for kw in node.keywords:
                if kw.arg == "timestamp":
                    # 找到了 timestamp 参数！
                    # 创建 `extra` 关键字参数
                    extra_kw = ast.keyword(
                        arg="extra",
                        value=ast.Dict(  # value 是一个字典
                            keys=[
                                ast.Constant(value="timestamp")
                            ],  # key 是字符串 'timestamp'
                            values=[kw.value],  # value 是旧的 timestamp 参数的值
                        ),
                    )
                    new_keywords.append(extra_kw)
                    break  # 找到了就跳出

            # 4. 组装成一个新的 Call 节点并返回，它将替换掉旧节点
            return ast.Call(
                func=new_func,
                args=[message_arg],  # args 是一个列表
                keywords=new_keywords,  # keywords 也是一个列表
            )

        # 如果不是我们想修改的函数调用，保持原样
        return node


# 3. 执行“解析 -> 转换 -> 生成”的流程
tree = ast.parse(source_code)

migrator = APIMigrator()
new_tree = migrator.visit(tree)
ast.fix_missing_locations(new_tree)  # 别忘了修复位置

new_code = ast.unparse(new_tree)

print("------ Original Code ------")
print(source_code)
print("\n------ Transformed Code ------")
print(new_code)
