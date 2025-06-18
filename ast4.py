"""
A script to find unused local variables in Python functions using AST.

This script parses a Python source file, builds an index of variable
definitions and usages within each function, and then reports any
variables that were defined but never used.
"""

import ast
from dataclasses import dataclass, field

# Global constants should be in uppercase.
SOURCE_CODE = """
def process_data(data, config):
    # 'config' is used
    if config.get('debug'):
        print("Processing...")

    # 'is_valid' is defined but never used
    is_valid = True

    # 'result' is defined and used
    result = len(data)
    return result

def calculate_total(items):
    # 'total' is defined and used
    total = 0
    # 'i' is defined (in comprehension) but only used inside it
    # 'item_price' is defined and used
    prices = [item_price for i, item_price in enumerate(items)]

    # 'tax' is defined but never used
    tax = 0.1

    for p in prices:
        total += p
    return total
"""


@dataclass
class ScopeInfo:
    """Holds variable usage information (defined vs. used) for a scope."""

    defined_vars: set[str] = field(default_factory=set)
    used_vars: set[str] = field(default_factory=set)


class AstIndexer(ast.NodeVisitor):
    """
    Visits an AST to index variable usage within each function scope.

    This visitor populates a dictionary mapping function nodes to ScopeInfo
    objects. These objects detail the defined and used variables for that
    scope.
    """

    def __init__(self) -> None:
        """Initializes the AstIndexer."""
        self.var_usage_index: dict[ast.FunctionDef, ScopeInfo] = {}
        self.current_function: ast.FunctionDef | None = None

    # Pylint is disabled for this special naming convention.
    # pylint: disable=invalid-name
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """
        Visits a FunctionDef node, setting the current scope and processing
        its children nodes.
        """
        self.current_function = node
        self.var_usage_index[node] = ScopeInfo()

        for arg in node.args.args:
            self.var_usage_index[node].defined_vars.add(arg.arg)

        self.generic_visit(node)
        self.current_function = None

    # pylint: disable=invalid-name
    def visit_Name(self, node: ast.Name) -> None:
        """
        Visits a Name node, recording its definition (Store context) or
        usage (Load context) in the current function scope.
        """
        if self.current_function:
            scope_info_obj = self.var_usage_index[self.current_function]
            if isinstance(node.ctx, ast.Store):
                scope_info_obj.defined_vars.add(node.id)
            elif isinstance(node.ctx, ast.Load):
                scope_info_obj.used_vars.add(node.id)


# --- 1. Parsing ---
tree = ast.parse(SOURCE_CODE)

# --- 2. Index Building ---
print("--- Pass 1: Building AST Index ---")
indexer = AstIndexer()
indexer.visit(tree)
print("Index built successfully.")

# --- 3. Analysis ---
print("\n--- Pass 2: Analyzing the Index ---")
for func_node, scope_info in indexer.var_usage_index.items():
    unused_vars = sorted(list(scope_info.defined_vars - scope_info.used_vars))
    if unused_vars:
        func_name = func_node.name
        line_num = func_node.lineno
        print(
            f"In function '{func_name}' (line {line_num}), "
            f"unused variables: {unused_vars}"
        )
