"""
可视化服务
"""

from typing import Dict, List, Any
from ..models.ast_models import (
    ASTNodeInfo,
    ASTConnection,
    ASTStructure,
    VisualProperties,
)


class VisualizationService:
    """可视化服务类"""

    @staticmethod
    def get_node_visual_properties(node_type: str) -> VisualProperties:
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

        props = properties.get(
            node_type, {"shape": "sphere", "color": "#888888", "size": 0.5}
        )
        return VisualProperties(
            shape=props["shape"], color=props["color"], size=props["size"]
        )

    @staticmethod
    def extract_ast_structure(ast_dict: Dict[str, Any]) -> ASTStructure:
        """提取AST结构信息，用于渲染"""
        nodes = []
        connections = []

        def traverse(node, parent_id=None):
            if not isinstance(node, dict) or "node_type" not in node:
                return

            node_id = str(id(node))
            node_type = node.get("node_type", "Unknown")

            # 获取节点的可视化属性
            visual_props = VisualizationService.get_node_visual_properties(node_type)

            # 提取节点信息
            node_info = ASTNodeInfo(
                id=node_id,
                node_type=node_type,
                name=node.get("name", ""),
                value=str(node.get("value", "")) if "value" in node else "",
                visual=visual_props,
                properties={},
            )

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
                        node_info.properties[key] = value

            nodes.append(node_info)

            # 创建父子连接
            if parent_id is not None:
                connections.append(ASTConnection(from_id=parent_id, to_id=node_id))

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

        return ASTStructure(nodes=nodes, connections=connections)

    @staticmethod
    def get_node_color_2d(node_type: str) -> str:
        """获取2D节点颜色"""
        colors = {
            "Module": "#00d4ff",
            "FunctionDef": "#ff6b6b",
            "ClassDef": "#ff9500",
            "If": "#ffd93d",
            "For": "#4ecdc4",
            "While": "#45b7d1",
            "Try": "#96ceb4",
            "Assign": "#95e1d3",
            "Return": "#f38ba8",
            "Call": "#a8e6cf",
            "Name": "#90caf9",
            "Constant": "#a5d6a7",
        }
        return colors.get(node_type, "#888888")

    @staticmethod
    def get_node_size_2d(node_type: str) -> int:
        """获取2D节点大小"""
        sizes = {
            "Module": 60,
            "FunctionDef": 50,
            "ClassDef": 50,
            "If": 40,
            "For": 40,
            "While": 40,
            "Try": 40,
            "Assign": 35,
            "Return": 35,
            "Call": 30,
            "Name": 25,
            "Constant": 25,
        }
        return sizes.get(node_type, 30)
