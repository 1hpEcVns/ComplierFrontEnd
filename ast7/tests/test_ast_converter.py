"""
AST转换器测试
"""

import unittest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils.ast_converter import parse_code_to_ast, ast_to_code


class TestASTConverter(unittest.TestCase):
    """AST转换器测试类"""

    def test_simple_function_parsing(self):
        """测试简单函数解析"""
        code = """
def hello_world():
    print("Hello, World!")
"""
        ast_dict = parse_code_to_ast(code)

        # 验证AST结构
        self.assertEqual(ast_dict["node_type"], "Module")
        self.assertIn("body", ast_dict)
        self.assertEqual(len(ast_dict["body"]), 1)

        func_def = ast_dict["body"][0]
        self.assertEqual(func_def["node_type"], "FunctionDef")
        self.assertEqual(func_def["name"], "hello_world")

    def test_round_trip_conversion(self):
        """测试双向转换"""
        original_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        # 解析为AST
        ast_dict = parse_code_to_ast(original_code)

        # 转换回代码
        generated_code = ast_to_code(ast_dict)

        # 验证生成的代码可以解析
        ast_dict_2 = parse_code_to_ast(generated_code)
        self.assertEqual(ast_dict["node_type"], ast_dict_2["node_type"])

    def test_syntax_error_handling(self):
        """测试语法错误处理"""
        invalid_code = "def invalid_function("

        with self.assertRaises(ValueError):
            parse_code_to_ast(invalid_code)


if __name__ == "__main__":
    unittest.main()
