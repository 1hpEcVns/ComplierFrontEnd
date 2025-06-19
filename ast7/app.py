import ast
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import io
import contextlib

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


# --- API Endpoints ---


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/parse", methods=["POST"])
def parse_code():
    """接收Python代码，返回其AST的JSON表示"""
    source_code = request.json["code"]
    try:
        tree = ast.parse(source_code)
        ast_json = ast_to_dict(tree)
        return jsonify(ast_json)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/unparse", methods=["POST"])
def unparse_ast():
    """接收AST的JSON表示，返回Python代码"""
    ast_json = request.json["ast"]
    try:
        tree = dict_to_ast(ast_json)
        # 修复可能丢失的位置信息，让 unparse 更健壮
        ast.fix_missing_locations(tree)
        code = ast.unparse(tree)
        return jsonify({"code": code})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/execute", methods=["POST"])
def execute_code():
    """
    接收Python代码，执行它并返回标准输出
    **警告：在生产环境中使用 exec 是极其危险的！**
    """
    code = request.json["code"]
    # 创建一个安全的沙箱来捕获输出
    stdout_capture = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_capture):
            exec(code, {})  # 在一个空的环境中执行
        output = stdout_capture.getvalue()
        return jsonify({"output": output})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5001)
