import ast
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import io
import contextlib
import copy

app = Flask(__name__, static_folder="", template_folder="")
CORS(app)  # 允许跨域请求，方便前后端开发

# --- AST 与 字典 互相转换的核心函数 ---


def ast_to_dict(node: ast.AST) -> dict | list | str:
    if not isinstance(node, ast.AST):
        return node
    node_type = node.__class__.__name__
    result = {"node_type": node_type}
    # 添加行列号信息，对于调试非常有用
    if hasattr(node, "lineno"):
        result["lineno"] = node.lineno
    if hasattr(node, "col_offset"):
        result["col_offset"] = node.col_offset

    for field in node._fields:
        value = getattr(node, field)
        if isinstance(value, list):
            result[field] = [ast_to_dict(item) for item in value]
        else:
            result[field] = ast_to_dict(value)
    return result


# 这是最棘手的部分：将字典递归地转回 AST 节点
def dict_to_ast(d: dict | list | str):
    if isinstance(d, list):
        return [dict_to_ast(item) for item in d]
    if not isinstance(d, dict) or "node_type" not in d:
        return d

    node_type = d.pop("node_type")
    # 从标准 ast 模块中找到对应的节点类，例如 ast.FunctionDef
    NodeClass = getattr(ast, node_type)

    # 移除我们添加的辅助字段
    d.pop("lineno", None)
    d.pop("col_offset", None)

    # 递归地为所有子字段转换
    for key, value in d.items():
        d[key] = dict_to_ast(value)

    # 用转换后的子字段实例化节点类
    # 注意：这里假设字典的键与 AST 节点的构造函数参数完全匹配
    return NodeClass(**d)


# --- AST 转换函数 ---


def rename_function_in_ast(node, old_name, new_name):
    """重命名函数"""
    if isinstance(node, dict):
        if node.get("node_type") == "FunctionDef" and node.get("name") == old_name:
            node["name"] = new_name
        if (
            node.get("node_type") == "Call"
            and isinstance(node.get("func"), dict)
            and node["func"].get("node_type") == "Name"
            and node["func"].get("id") == old_name
        ):
            node["func"]["id"] = new_name

        # 递归处理子节点
        for key, value in node.items():
            if isinstance(value, list):
                for item in value:
                    rename_function_in_ast(item, old_name, new_name)
            elif isinstance(value, dict):
                rename_function_in_ast(value, old_name, new_name)
    elif isinstance(node, list):
        for item in node:
            rename_function_in_ast(item, old_name, new_name)


def add_logging_to_functions(node, log_message="Function called"):
    """为所有函数添加日志输出"""
    if isinstance(node, dict):
        if node.get("node_type") == "FunctionDef":
            # 创建日志语句 AST
            log_stmt = {
                "node_type": "Expr",
                "value": {
                    "node_type": "Call",
                    "func": {
                        "node_type": "Name",
                        "id": "print",
                        "ctx": {"node_type": "Load"},
                    },
                    "args": [
                        {
                            "node_type": "Constant",
                            "value": f"{log_message}: {node.get('name', 'unknown')}",
                        }
                    ],
                    "keywords": [],
                },
            }
            # 将日志语句插入到函数体的开头
            if "body" in node and isinstance(node["body"], list):
                node["body"].insert(0, log_stmt)

        # 递归处理子节点
        for key, value in node.items():
            if isinstance(value, list):
                for item in value:
                    add_logging_to_functions(item, log_message)
            elif isinstance(value, dict):
                add_logging_to_functions(value, log_message)
    elif isinstance(node, list):
        for item in node:
            add_logging_to_functions(item, log_message)


def replace_constants(node, old_value, new_value):
    """替换常量值"""
    if isinstance(node, dict):
        if node.get("node_type") == "Constant" and str(node.get("value")) == str(
            old_value
        ):
            node["value"] = new_value

        # 递归处理子节点
        for key, value in node.items():
            if isinstance(value, list):
                for item in value:
                    replace_constants(item, old_value, new_value)
            elif isinstance(value, dict):
                replace_constants(value, old_value, new_value)
    elif isinstance(node, list):
        for item in node:
            replace_constants(item, old_value, new_value)


def remove_statements_by_type(node, stmt_type):
    """删除指定类型的语句"""
    if isinstance(node, dict):
        if "body" in node and isinstance(node["body"], list):
            node["body"] = [
                stmt
                for stmt in node["body"]
                if not (isinstance(stmt, dict) and stmt.get("node_type") == stmt_type)
            ]

        # 递归处理子节点
        for key, value in node.items():
            if isinstance(value, list):
                for item in value:
                    remove_statements_by_type(item, stmt_type)
            elif isinstance(value, dict):
                remove_statements_by_type(value, stmt_type)
    elif isinstance(node, list):
        for item in node:
            remove_statements_by_type(item, stmt_type)


# --- API Endpoints ---


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/parse", methods=["POST"])
def parse_code():
    """接收Python代码，返回其AST的JSON表示"""
    try:
        source_code = request.json["code"]
        tree = ast.parse(source_code)
        ast_json = ast_to_dict(tree)
        return jsonify({"success": True, "ast": ast_json})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/unparse", methods=["POST"])
def unparse_ast():
    """接收AST的JSON表示，返回Python代码"""
    try:
        ast_json = request.json["ast"]
        tree = dict_to_ast(copy.deepcopy(ast_json))
        # 修复可能丢失的位置信息，让 unparse 更健壮
        ast.fix_missing_locations(tree)
        code = ast.unparse(tree)
        return jsonify({"success": True, "code": code})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/execute", methods=["POST"])
def execute_code():
    """
    接收Python代码，执行它并返回标准输出
    **警告：在生产环境中使用 exec 是极其危险的！**
    """
    try:
        code = request.json["code"]
        # 创建一个安全的沙箱来捕获输出
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(
            stderr_capture
        ):
            exec(code, {})  # 在一个空的环境中执行

        output = stdout_capture.getvalue()
        error_output = stderr_capture.getvalue()

        return jsonify(
            {
                "success": True,
                "output": output,
                "error": error_output if error_output else None,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/transform", methods=["POST"])
def transform_ast():
    """应用指定的转换操作到AST"""
    try:
        data = request.json
        ast_json = copy.deepcopy(data["ast"])
        operation = data["operation"]
        params = data.get("params", {})

        if operation == "rename_function":
            rename_function_in_ast(ast_json, params["old_name"], params["new_name"])
        elif operation == "add_logging":
            add_logging_to_functions(ast_json, params.get("message", "Function called"))
        elif operation == "replace_constants":
            replace_constants(ast_json, params["old_value"], params["new_value"])
        elif operation == "remove_statements":
            remove_statements_by_type(ast_json, params["statement_type"])
        else:
            return (
                jsonify({"success": False, "error": f"Unknown operation: {operation}"}),
                400,
            )

        return jsonify({"success": True, "ast": ast_json})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/save_workflow", methods=["POST"])
def save_workflow():
    """保存工作流配置"""
    try:
        workflow_data = request.json
        workflow_name = workflow_data.get("name", "workflow")

        # 在实际应用中，这里应该保存到数据库
        # 现在我们只是返回成功响应
        return jsonify(
            {
                "success": True,
                "message": f"Workflow '{workflow_name}' saved successfully",
                "workflow_id": f"wf_{workflow_name}_{hash(str(workflow_data)) % 10000}",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/load_workflow", methods=["POST"])
def load_workflow():
    """加载工作流配置"""
    try:
        workflow_id = request.json.get("workflow_id")

        # 在实际应用中，这里应该从数据库加载
        # 现在我们返回一个示例工作流
        sample_workflow = {
            "name": "Sample Workflow",
            "operations": [
                {
                    "type": "rename_function",
                    "params": {"old_name": "hello", "new_name": "greet"},
                },
                {"type": "add_logging", "params": {"message": "Function executed"}},
            ],
        }

        return jsonify({"success": True, "workflow": sample_workflow})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5001)
