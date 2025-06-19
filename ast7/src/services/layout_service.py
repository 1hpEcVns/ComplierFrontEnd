"""
布局计算服务
"""

import math
from typing import Dict, List, Any, Tuple
from ..models.ast_models import Position2D, Position3D, ASTNodeInfo


class LayoutService:
    """布局计算服务类"""

    @staticmethod
    def calculate_2d_positions(
        ast_dict: Dict[str, Any], layout_type: str = "tree"
    ) -> Dict[int, Position2D]:
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
            positions = LayoutService._calculate_tree_layout_2d(nodes)
        elif layout_type == "radial":
            positions = LayoutService._calculate_radial_layout_2d(nodes)
        elif layout_type == "grid":
            positions = LayoutService._calculate_grid_layout_2d(nodes)
        else:
            positions = LayoutService._calculate_tree_layout_2d(nodes)

        return positions

    @staticmethod
    def _calculate_tree_layout_2d(nodes: List[Dict]) -> Dict[int, Position2D]:
        """树形布局"""
        positions = {}
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
                positions[id(node["data"])] = Position2D(x=x, y=y, depth=depth)

        return positions

    @staticmethod
    def _calculate_radial_layout_2d(nodes: List[Dict]) -> Dict[int, Position2D]:
        """径向布局"""
        positions = {}
        center_x, center_y = 400, 300
        max_radius = 250

        for i, node in enumerate(nodes):
            if i == 0:
                positions[id(node["data"])] = Position2D(
                    x=center_x, y=center_y, depth=0
                )
            else:
                radius = min(node["depth"] * 80, max_radius)
                angle = (i / len(nodes)) * 2 * math.pi
                x = center_x + math.cos(angle) * radius
                y = center_y + math.sin(angle) * radius
                positions[id(node["data"])] = Position2D(x=x, y=y, depth=node["depth"])

        return positions

    @staticmethod
    def _calculate_grid_layout_2d(nodes: List[Dict]) -> Dict[int, Position2D]:
        """网格布局"""
        positions = {}
        width, height = 800, 600
        cols = math.ceil(math.sqrt(len(nodes)))
        cell_width = width / cols
        cell_height = height / math.ceil(len(nodes) / cols)

        for i, node in enumerate(nodes):
            col = i % cols
            row = i // cols
            x = (col + 0.5) * cell_width
            y = (row + 0.5) * cell_height
            positions[id(node["data"])] = Position2D(x=x, y=y, depth=node["depth"])

        return positions

    @staticmethod
    def calculate_3d_positions(
        ast_dict: Dict[str, Any], layout_type: str = "spiral"
    ) -> Dict[int, Position3D]:
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

            position = Position3D(x=x, y=y, z=z, depth=depth, index=current_index)
            positions[id(node)] = position

            # 递归处理子节点
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in [
                        "body",
                        "orelse",
                        "finalbody",
                        "handlers",
                    ] and isinstance(value, list):
                        for i, child in enumerate(value):
                            if isinstance(child, dict):
                                traverse(child, depth + 1, (x, y, z), i * 0.5)
                    elif isinstance(value, dict) and "node_type" in value:
                        traverse(value, depth + 1, (x, y, z), angle_offset + 1)

        if isinstance(ast_dict, dict):
            traverse(ast_dict)

        return positions
