# 可视化 AST 编辑器

## 1. 项目概述

这是一个非常棒且富有挑战性的想法！将抽象的 AST 操作与 n8n/Zapier 这种可视化、节点式的工作流结合起来，就创造出了一个**可视化的元编程工具**。这本质上就是图形化编程的精髓：**用流程图的方式来编排对代码本身的修改**。

这个项目比之前的要复杂得多，因为它需要一个前后端分离的 Web 应用。我们将构建一个简化版的概念验证 (PoC) 项目，它包含以下核心功能：

## 2. 项目结构

1. **后端 (Python + Flask)**：一个提供 API 的微型服务器，负责：
    * 将 Python 源码解析成 AST JSON。
    * 接收修改后的 AST JSON，将其“反解析”回 Python 源码。
    * 安全地执行生成的 Python 代码并返回结果。

2. **前端 (HTML + JS)**：一个模仿 n8n 界面的单页面应用，用户可以：
    * 在“源码”节点输入代码。
    * 在“转换”节点中通过点击按钮和输入文本来定义一个修改操作（例如，“重命名函数”）。
    * 在“结果”节点中看到修改后的新代码。
    * 点击“运行”按钮，将新代码发送到后端执行，并看到输出。

## 3. 后端 (Python + Flask)

这个服务器是整个系统的大脑。

**项目结构**:

```
visual-ast-editor/
|-- app.py         # Flask 后端服务器
|-- index.html     # 前端页面
```

**`app.py` 的代码**:

```python
import ast
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import io
import contextlib

app = Flask(__name__, static_folder='', template_folder='')
CORS(app) # 允许跨域请求，方便前后端开发

# --- AST 与 字典 互相转换的核心函数 ---

def ast_to_dict(node: ast.AST) -> dict | list | str:
    if not isinstance(node, ast.AST):
        return node
    node_type = node.__class__.__name__
    result = {"node_type": node_type}
    # 添加行列号信息，对于调试非常有用
    if hasattr(node, 'lineno'):
        result['lineno'] = node.lineno
    if hasattr(node, 'col_offset'):
        result['col_offset'] = node.col_offset
        
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
    if not isinstance(d, dict) or 'node_type' not in d:
        return d
    
    node_type = d.pop('node_type')
    # 从标准 ast 模块中找到对应的节点类，例如 ast.FunctionDef
    NodeClass = getattr(ast, node_type)
    
    # 移除我们添加的辅助字段
    d.pop('lineno', None)
    d.pop('col_offset', None)

    # 递归地为所有子字段转换
    for key, value in d.items():
        d[key] = dict_to_ast(value)
        
    # 用转换后的子字段实例化节点类
    # 注意：这里假设字典的键与 AST 节点的构造函数参数完全匹配
    return NodeClass(**d)


# --- API Endpoints ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/parse', methods=['POST'])
def parse_code():
    """接收Python代码，返回其AST的JSON表示"""
    source_code = request.json['code']
    try:
        tree = ast.parse(source_code)
        ast_json = ast_to_dict(tree)
        return jsonify(ast_json)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/unparse', methods=['POST'])
def unparse_ast():
    """接收AST的JSON表示，返回Python代码"""
    ast_json = request.json['ast']
    try:
        tree = dict_to_ast(ast_json)
        # 修复可能丢失的位置信息，让 unparse 更健壮
        ast.fix_missing_locations(tree)
        code = ast.unparse(tree)
        return jsonify({"code": code})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/execute', methods=['POST'])
def execute_code():
    """
    接收Python代码，执行它并返回标准输出
    **警告：在生产环境中使用 exec 是极其危险的！**
    """
    code = request.json['code']
    # 创建一个安全的沙箱来捕获输出
    stdout_capture = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_capture):
            exec(code, {}) # 在一个空的环境中执行
        output = stdout_capture.getvalue()
        return jsonify({"output": output})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5001)

```

## 4. 前端 (HTML + JS)

这个页面将模仿 n8n 的布局，用简单的 CSS 创建节点和连线。

**`index.html` 的代码**:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Visual AST Editor</title>
    <style>
        body { font-family: sans-serif; background-color: #f0f2f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .workflow { display: flex; align-items: center; gap: 20px; }
        .node { background: white; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 15px; width: 350px; }
        .node h3 { margin-top: 0; border-bottom: 1px solid #eee; padding-bottom: 10px; font-size: 16px; }
        textarea, pre { width: 100%; min-height: 200px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 14px; }
        pre { background-color: #fafafa; white-space: pre-wrap; word-wrap: break-word; }
        .arrow { font-size: 40px; color: #aaa; }
        button { background-color: #4CAF50; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; display: block; width: 100%; margin-top: 10px; }
        button:hover { background-color: #45a049; }
        .transform-group { margin-top: 15px; }
        .transform-group input { width: calc(50% - 10px); box-sizing: border-box; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
    </style>
</head>
<body>

<div class="workflow">
    <!-- Node 1: Source Code -->
    <div class="node">
        <h3>1. Source Code</h3>
        <textarea id="source-code">def hello(name):
    print(f"Hello, {name}")

hello("World")</textarea>
        <button id="parse-btn">Parse Code</button>
    </div>

    <div class="arrow">&rarr;</div>

    <!-- Node 2: Transformation -->
    <div class="node">
        <h3>2. AST Transformation</h3>
        <div class="transform-group">
            <label>Rename Function:</label><br>
            <input type="text" id="old-name" placeholder="Old Name">
            <input type="text" id="new-name" placeholder="New Name">
        </div>
        <button id="apply-btn">Apply & Unparse</button>
    </div>

    <div class="arrow">&rarr;</div>

    <!-- Node 3: Result -->
    <div class="node">
        <h3>3. Generated Code & Output</h3>
        <label>New Code:</label>
        <pre id="result-code"></pre>
        <button id="run-btn">Run Code</button>
        <label>Output:</label>
        <pre id="output" style="min-height: 50px; background-color: #333; color: #fff;"></pre>
    </div>
</div>

<script>
    const API_URL = 'http://127.0.0.1:5001/api';
    let currentAstJson = null;

    // --- DOM Elements ---
    const sourceCodeEl = document.getElementById('source-code');
    const parseBtn = document.getElementById('parse-btn');
    const applyBtn = document.getElementById('apply-btn');
    const runBtn = document.getElementById('run-btn');
    const resultCodeEl = document.getElementById('result-code');
    const outputEl = document.getElementById('output');

    // --- API Call Functions ---
    async function apiCall(endpoint, body) {
        try {
            const response = await fetch(`${API_URL}/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            return data;
        } catch (error) {
            alert(`Error: ${error.message}`);
            return null;
        }
    }

    // --- Transformation Logic (Client-side) ---
    function renameFunctionInAst(node, oldName, newName) {
        if (typeof node !== 'object' || node === null) return;

        // If this is a function definition with the old name, change it
        if (node.node_type === 'FunctionDef' && node.name === oldName) {
            node.name = newName;
        }
        // If this is a function call with the old name, change it
        if (node.node_type === 'Call' && node.func.node_type === 'Name' && node.func.id === oldName) {
            node.func.id = newName;
        }
        
        // Recurse into children
        for (const key in node) {
            if (Array.isArray(node[key])) {
                node[key].forEach(child => renameFunctionInAst(child, oldName, newName));
            } else if (typeof node[key] === 'object') {
                renameFunctionInAst(node[key], oldName, newName);
            }
        }
    }

    // --- Event Listeners ---
    parseBtn.addEventListener('click', async () => {
        const data = await apiCall('parse', { code: sourceCodeEl.value });
        if (data) {
            currentAstJson = data;
            alert('Code parsed successfully! AST is ready for transformation.');
        }
    });

    applyBtn.addEventListener('click', async () => {
        if (!currentAstJson) {
            alert('Please parse the code first!');
            return;
        }

        const oldName = document.getElementById('old-name').value;
        const newName = document.getElementById('new-name').value;

        if (!oldName || !newName) {
            alert('Please provide both old and new function names.');
            return;
        }
        
        // Modify the AST JSON in memory
        renameFunctionInAst(currentAstJson, oldName, newName);
        
        const data = await apiCall('unparse', { ast: currentAstJson });
        if (data) {
            resultCodeEl.textContent = data.code;
        }
    });

    runBtn.addEventListener('click', async () => {
        const codeToRun = resultCodeEl.textContent;
        if (!codeToRun) {
            alert('No code to run. Please generate it first.');
            return;
        }
        const data = await apiCall('execute', { code: codeToRun });
        if (data) {
            outputEl.textContent = data.output || data.error || '';
        }
    });
</script>
</body>
</html>

```

## 5. 如何运行

1. **安装依赖**:

    ```bash
    pip install Flask Flask-Cors
    ```

2. **启动后端服务器**:
    在你的项目文件夹 (`visual-ast-editor`) 中，打开终端并运行：

    ```bash
    python app.py
    ```

    你会看到服务器在 `http://127.0.0.1:5001` 上启动。

3. **打开前端页面**:
    在浏览器中直接打开 `index.html` 文件，或者访问 `http://127.0.0.1:5001/`。

4. **操作流程**:
    a.  页面加载后，源码已填好。点击 **"Parse Code"** 按钮。你会收到一个成功的弹窗。
    b.  在中间的“转换”节点，**Old Name** 输入 `hello`，**New Name** 输入 `say_greeting`。
    c.  点击 **"Apply & Unparse"** 按钮。右侧“结果”节点的代码区域会显示出函数名和调用都被修改过的新代码。
    d.  点击 **"Run Code"** 按钮，下方的“Output”区域会显示新代码的运行结果 `Hello, World`。

---

## 6. 后续扩展方向

这个 PoC 项目为你打开了一扇大门，可以向很多方向扩展：

1. **真正的节点库**：使用 **React Flow** 或 **Svelte Flow** 替换掉简单的 CSS 布局，实现节点的拖拽、连接和动态添加。
2. **更多转换操作**：增加“插入日志”、“删除语句”、“修改常量”等节点，每个节点都有自己的UI。
3. **AST 可视化**：将第一个节点解析后的 AST JSON 用 `json-viewer-js` 库（如上一个例子）展示出来，让用户可以直观地看到树的变化。
4. **错误处理**：在前端更友好地展示来自后端的错误信息。
5. **工作流保存/加载**：将定义好的一系列转换操作保存成一个 JSON，可以随时加载回来应用到不同的代码上。
