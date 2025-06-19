"""
AST数据模型定义
"""

import ast
from typing import Dict, List, Any, Union, Optional
from dataclasses import dataclass


@dataclass
class Position2D:
    """2D位置信息"""

    x: float
    y: float
    depth: int = 0


@dataclass
class Position3D:
    """3D位置信息"""

    x: float
    y: float
    z: float
    depth: int = 0
    index: int = 0


@dataclass
class VisualProperties:
    """节点可视化属性"""

    shape: str
    color: str
    size: float


@dataclass
class ASTNodeInfo:
    """AST节点信息"""

    id: str
    node_type: str
    name: str = ""
    value: str = ""
    properties: Dict[str, Any] = None
    visual: VisualProperties = None
    position_2d: Position2D = None
    position_3d: Position3D = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class ASTConnection:
    """AST节点连接信息"""

    from_id: str
    to_id: str
    connection_type: str = "parent-child"


@dataclass
class ASTStructure:
    """完整的AST结构"""

    nodes: List[ASTNodeInfo]
    connections: List[ASTConnection]
    layout_type: str = "tree"
