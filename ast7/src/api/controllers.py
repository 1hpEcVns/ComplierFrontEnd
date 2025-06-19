"""
API控制器
"""

import json
from flask import Blueprint, request, jsonify
from ..utils.ast_converter import parse_code_to_ast, ast_to_code
from ..services.layout_service import LayoutService
from ..services.visualization_service import VisualizationService
from ..services.transform_service import TransformService
from ..services.code_execution_service import CodeExecutionService


# 创建蓝图
api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/parse", methods=["POST"])
def parse_code():
    """解析Python代码为AST"""
    try:
        data = request.get_json()
        source_code = data.get("code", "")

        if not source_code.strip():
            return jsonify({"success": False, "error": "代码不能为空"}), 400

        # 解析代码
        ast_json = parse_code_to_ast(source_code)

        return jsonify({"success": True, "ast": ast_json})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/parse_2d", methods=["POST"])
def parse_code_2d():
    """解析代码并返回适合2D渲染的结构"""
    try:
        data = request.get_json()
        source_code = data.get("code", "")
        layout_type = data.get("layout", "tree")

        if not source_code.strip():
            return jsonify({"success": False, "error": "代码不能为空"}), 400

        # 解析代码
        ast_json = parse_code_to_ast(source_code)

        # 计算2D位置
        positions = LayoutService.calculate_2d_positions(ast_json, layout_type)

        # 提取结构信息
        structure = VisualizationService.extract_ast_structure(ast_json)

        # 合并位置信息
        for node in structure.nodes:
            node_id = int(node.id)
            if node_id in positions:
                node.position_2d = positions[node_id]

        return jsonify(
            {
                "success": True,
                "ast": ast_json,
                "structure": {
                    "nodes": [node.__dict__ for node in structure.nodes],
                    "connections": [conn.__dict__ for conn in structure.connections],
                },
                "layout": layout_type,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/parse_3d", methods=["POST"])
def parse_code_3d():
    """解析代码并返回适合3D渲染的结构"""
    try:
        data = request.get_json()
        source_code = data.get("code", "")
        layout_type = data.get("layout", "spiral")

        if not source_code.strip():
            return jsonify({"success": False, "error": "代码不能为空"}), 400

        # 解析代码
        ast_json = parse_code_to_ast(source_code)

        # 计算3D位置
        positions = LayoutService.calculate_3d_positions(ast_json, layout_type)

        # 提取结构信息
        structure = VisualizationService.extract_ast_structure(ast_json)

        # 合并位置信息
        for node in structure.nodes:
            node_id = int(node.id)
            if node_id in positions:
                node.position_3d = positions[node_id]

        return jsonify(
            {
                "success": True,
                "ast": ast_json,
                "structure": {
                    "nodes": [node.__dict__ for node in structure.nodes],
                    "connections": [conn.__dict__ for conn in structure.connections],
                },
                "layout": layout_type,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/unparse", methods=["POST"])
def unparse_ast():
    """将AST转换回Python代码"""
    try:
        data = request.get_json()
        ast_dict = data.get("ast")

        if not ast_dict:
            return jsonify({"success": False, "error": "AST数据不能为空"}), 400

        # 转换回代码
        code = ast_to_code(ast_dict)

        return jsonify({"success": True, "code": code})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/execute", methods=["POST"])
def execute_code():
    """执行Python代码"""
    try:
        data = request.get_json()
        code = data.get("code", "")

        if not code.strip():
            return jsonify({"success": False, "error": "代码不能为空"}), 400

        # 执行代码
        result = CodeExecutionService.execute_code(code)

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/transform", methods=["POST"])
def transform_ast():
    """转换AST"""
    try:
        data = request.get_json()
        ast_dict = data.get("ast")
        operation = data.get("operation")
        params = data.get("params", {})

        if not ast_dict:
            return jsonify({"success": False, "error": "AST数据不能为空"}), 400
        if not operation:
            return jsonify({"success": False, "error": "操作类型不能为空"}), 400

        # 执行转换
        if operation == "rename_function":
            result = TransformService.rename_function_in_ast(
                ast_dict, params.get("old_name", ""), params.get("new_name", "")
            )
        elif operation == "add_logging":
            result = TransformService.add_logging_to_functions(
                ast_dict, params.get("log_message", "Function called")
            )
        elif operation == "replace_constants":
            result = TransformService.replace_constants(
                ast_dict, params.get("old_value"), params.get("new_value")
            )
        elif operation == "remove_statements":
            result = TransformService.remove_statements_by_type(
                ast_dict, params.get("stmt_type", "")
            )
        else:
            return jsonify({"success": False, "error": f"未知操作: {operation}"}), 400

        return jsonify({"success": True, "ast": result})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/transforms", methods=["GET"])
def get_available_transforms():
    """获取可用的转换操作"""
    try:
        transforms = TransformService.get_available_transforms()
        return jsonify({"success": True, "transforms": transforms})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/execution-limits", methods=["GET"])
def get_execution_limits():
    """获取代码执行限制信息"""
    try:
        limits = CodeExecutionService.get_execution_limits()
        return jsonify({"success": True, "limits": limits})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/validate", methods=["POST"])
def validate_code():
    """验证代码语法"""
    try:
        data = request.get_json()
        code = data.get("code", "")

        if not code.strip():
            return jsonify({"success": False, "error": "代码不能为空"}), 400

        # 验证代码
        is_valid, message = CodeExecutionService.validate_code(code)

        return jsonify({"success": True, "valid": is_valid, "message": message})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
