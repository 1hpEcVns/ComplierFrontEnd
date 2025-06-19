import ast
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import io
import contextlib
import copy
import math

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


# --- 3D 可视化专用函数 ---


def calculate_2d_positions(ast_dict, layout_type="tree"):
    """计算AST节点的2D位置"""
    positions = {}
    nodes = []

    def extract_nodes(node, parent=None, depth=0):
        if not isinstance(node, dict) or "node_type" not in node:
            return

        node_info = {
            "id": len(nodes),
            "data": node,
            "parent": parent,
            "depth": depth,
            "children": [],
        }
        nodes.append(node_info)

        # 处理子节点
        for key, value in node.items():
            if key in ["body", "orelse", "finalbody", "handlers"] and isinstance(
                value, list
            ):
                for child in value:
                    if isinstance(child, dict) and "node_type" in child:
                        child_info = extract_nodes(child, node_info, depth + 1)
                        if child_info:
                            node_info["children"].append(child_info)
            elif isinstance(value, dict) and "node_type" in value:
                child_info = extract_nodes(value, node_info, depth + 1)
                if child_info:
                    node_info["children"].append(child_info)

        return node_info

    if isinstance(ast_dict, dict):
        extract_nodes(ast_dict)

    # 计算布局
    if layout_type == "tree":
        # 树形布局
        levels = {}
        for node in nodes:
            if node["depth"] not in levels:
                levels[node["depth"]] = []
            levels[node["depth"]].append(node)

        width, height = 800, 600
        for depth, level_nodes in levels.items():
            y = (height / (len(levels) + 1)) * (depth + 1)
            for i, node in enumerate(level_nodes):
                x = (width / (len(level_nodes) + 1)) * (i + 1)
                positions[id(node["data"])] = {"x": x, "y": y, "depth": depth}

    elif layout_type == "radial":
        # 径向布局
        import math

        center_x, center_y = 400, 300
        max_radius = 250

        for i, node in enumerate(nodes):
            if i == 0:
                positions[id(node["data"])] = {"x": center_x, "y": center_y, "depth": 0}
            else:
                radius = min(node["depth"] * 80, max_radius)
                angle = (i / len(nodes)) * 2 * math.pi
                x = center_x + math.cos(angle) * radius
                y = center_y + math.sin(angle) * radius
                positions[id(node["data"])] = {"x": x, "y": y, "depth": node["depth"]}

    return positions


def calculate_3d_positions(ast_dict, layout_type="spiral"):
    """计算AST节点的3D位置"""
    positions = {}
    node_index = 0

    def traverse(node, depth=0, parent_pos=None, angle_offset=0):
        nonlocal node_index
        current_index = node_index
        node_index += 1

        if layout_type == "spiral":
            # 螺旋布局
            radius = depth * 3 + 2
            angle = (current_index * 2.4 + angle_offset) % (math.pi * 2)
            x = math.cos(angle) * radius
            z = math.sin(angle) * radius
            y = -depth * 2
        elif layout_type == "tree":
            # 树形布局
            if parent_pos is None:
                x, y, z = 0, 0, 0
            else:
                sibling_offset = (current_index % 4 - 1.5) * 2
                x = parent_pos[0] + sibling_offset
                y = parent_pos[1] - 3
                z = parent_pos[2] + (depth % 2) * 2
        elif layout_type == "circular":
            # 圆形分层布局
            radius = depth * 4 + 3
            angle = (current_index * math.pi * 0.618) % (math.pi * 2)  # 黄金角
            x = math.cos(angle) * radius
            z = math.sin(angle) * radius
            y = math.sin(depth * 0.5) * 2
        else:
            # 默认网格布局
            x = (current_index % 5 - 2) * 3
            y = -depth * 2
            z = (current_index // 5) * 3

        position = {"x": x, "y": y, "z": z, "depth": depth, "index": current_index}
        positions[id(node)] = position

        # 递归处理子节点
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ["body", "orelse", "finalbody", "handlers"] and isinstance(
                    value, list
                ):
                    for i, child in enumerate(value):
                        if isinstance(child, dict):
                            traverse(child, depth + 1, (x, y, z), i * 0.5)
                elif isinstance(value, dict) and "node_type" in value:
                    traverse(value, depth + 1, (x, y, z), angle_offset + 1)

    if isinstance(ast_dict, dict):
        traverse(ast_dict)

    return positions


def get_node_visual_properties(node_type):
    """根据节点类型返回可视化属性"""
    properties = {
        "Module": {"shape": "sphere", "color": "#00d4ff", "size": 0.8},
        "FunctionDef": {"shape": "box", "color": "#ff6b6b", "size": 1.2},
        "ClassDef": {"shape": "cylinder", "color": "#ff9500", "size": 1.0},
        "If": {"shape": "cone", "color": "#ffd93d", "size": 1.0},
        "For": {"shape": "torus", "color": "#4ecdc4", "size": 0.8},
        "While": {"shape": "torus", "color": "#45b7d1", "size": 0.8},
        "Try": {"shape": "octahedron", "color": "#96ceb4", "size": 0.9},
        "Assign": {"shape": "cylinder", "color": "#95e1d3", "size": 0.7},
        "AugAssign": {"shape": "cylinder", "color": "#a8e6cf", "size": 0.7},
        "Return": {"shape": "octahedron", "color": "#f38ba8", "size": 0.8},
        "Break": {"shape": "tetrahedron", "color": "#ff8a80", "size": 0.6},
        "Continue": {"shape": "tetrahedron", "color": "#82b1ff", "size": 0.6},
        "Call": {"shape": "icosahedron", "color": "#a8e6cf", "size": 0.7},
        "BinOp": {"shape": "dodecahedron", "color": "#ffd180", "size": 0.6},
        "UnaryOp": {"shape": "tetrahedron", "color": "#ff9d80", "size": 0.5},
        "Compare": {"shape": "cylinder", "color": "#b39ddb", "size": 0.6},
        "Name": {"shape": "sphere", "color": "#90caf9", "size": 0.4},
        "Constant": {"shape": "sphere", "color": "#a5d6a7", "size": 0.4},
        "List": {"shape": "box", "color": "#ffcc02", "size": 0.6},
        "Dict": {"shape": "box", "color": "#ff6f00", "size": 0.6},
        "Set": {"shape": "sphere", "color": "#ff5722", "size": 0.5},
        "Tuple": {"shape": "box", "color": "#795548", "size": 0.6},
    }

    return properties.get(
        node_type, {"shape": "sphere", "color": "#888888", "size": 0.5}
    )


def extract_ast_structure(ast_dict):
    """提取AST结构信息，用于3D渲染"""
    nodes = []
    connections = []

    def traverse(node, parent_id=None):
        if not isinstance(node, dict) or "node_type" not in node:
            return

        node_id = id(node)
        node_type = node.get("node_type", "Unknown")

        # 获取节点的可视化属性
        visual_props = get_node_visual_properties(node_type)

        # 提取节点信息
        node_info = {
            "id": node_id,
            "type": node_type,
            "name": node.get("name", ""),
            "value": str(node.get("value", "")) if "value" in node else "",
            "visual": visual_props,
            "properties": {},
        }

        # 提取重要属性
        for key, value in node.items():
            if key not in [
                "node_type",
                "body",
                "orelse",
                "finalbody",
                "handlers",
                "lineno",
                "col_offset",
            ]:
                if not isinstance(value, (dict, list)):
                    node_info["properties"][key] = value

        nodes.append(node_info)

        # 创建父子连接
        if parent_id is not None:
            connections.append({"from": parent_id, "to": node_id})

        # 递归处理子节点
        for key, value in node.items():
            if key in ["body", "orelse", "finalbody", "handlers"] and isinstance(
                value, list
            ):
                for child in value:
                    traverse(child, node_id)
            elif isinstance(value, dict) and "node_type" in value:
                traverse(value, node_id)

    if isinstance(ast_dict, dict):
        traverse(ast_dict)

    return {"nodes": nodes, "connections": connections}


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


@app.route("/api/parse_2d", methods=["POST"])
def parse_code_2d():
    """解析代码并返回适合2D渲染的结构"""
    try:
        source_code = request.json["code"]
        layout_type = request.json.get("layout", "tree")

        tree = ast.parse(source_code)
        ast_json = ast_to_dict(tree)

        # 计算2D位置
        positions = calculate_2d_positions(ast_json, layout_type)

        # 提取结构信息
        structure = extract_ast_structure(ast_json)

        # 合并位置信息
        for node in structure["nodes"]:
            if node["id"] in positions:
                node["position"] = positions[node["id"]]
            else:
                node["position"] = {"x": 400, "y": 300, "depth": 0}

        return jsonify(
            {
                "success": True,
                "ast": ast_json,
                "structure": structure,
                "layout": layout_type,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/parse_3d", methods=["POST"])
def parse_code_3d():
    """解析代码并返回适合3D渲染的结构"""
    try:
        source_code = request.json["code"]
        layout_type = request.json.get("layout", "spiral")

        tree = ast.parse(source_code)
        ast_json = ast_to_dict(tree)

        # 计算3D位置
        positions = calculate_3d_positions(ast_json, layout_type)

        # 提取结构信息
        structure = extract_ast_structure(ast_json)

        # 合并位置信息
        for node in structure["nodes"]:
            if node["id"] in positions:
                node["position"] = positions[node["id"]]
            else:
                node["position"] = {"x": 0, "y": 0, "z": 0, "depth": 0, "index": 0}

        return jsonify(
            {
                "success": True,
                "ast": ast_json,
                "structure": structure,
                "layout": layout_type,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/update_layout", methods=["POST"])
def update_layout():
    """重新计算AST布局"""
    try:
        ast_json = request.json["ast"]
        layout_type = request.json.get("layout", "spiral")

        # 重新计算位置
        positions = calculate_3d_positions(ast_json, layout_type)

        # 提取结构信息
        structure = extract_ast_structure(ast_json)

        # 合并位置信息
        for node in structure["nodes"]:
            if node["id"] in positions:
                node["position"] = positions[node["id"]]

        return jsonify({"success": True, "structure": structure, "layout": layout_type})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/update_node", methods=["POST"])
def update_node():
    """更新单个节点的属性"""
    try:
        ast_json = request.json["ast"]
        node_id = request.json["node_id"]
        updates = request.json["updates"]

        # 递归查找并更新节点
        def find_and_update(node):
            if isinstance(node, dict) and id(node) == node_id:
                node.update(updates)
                return True
            elif isinstance(node, dict):
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        if find_and_update(value):
                            return True
            elif isinstance(node, list):
                for item in node:
                    if find_and_update(item):
                        return True
            return False

        if find_and_update(ast_json):
            return jsonify({"success": True, "ast": ast_json})
        else:
            return jsonify({"success": False, "error": "节点未找到"}), 404

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
