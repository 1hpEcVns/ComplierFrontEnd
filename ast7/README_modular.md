# 🌳 2D/3D AST可视化编辑器 (模块化版本)

一个现代化的Python抽象语法树（AST）可视化编辑工具，采用模块化架构设计，支持2D和3D可视化模式。

## 📁 项目结构

```
ast7/
├── src/                          # 源代码目录
│   ├── backend/                  # 后端模块
│   │   ├── __init__.py
│   │   └── app.py               # Flask应用
│   ├── api/                     # API控制器
│   │   ├── __init__.py
│   │   └── controllers.py       # API路由和控制器
│   ├── models/                  # 数据模型
│   │   ├── __init__.py
│   │   └── ast_models.py        # AST相关数据模型
│   ├── services/                # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── layout_service.py    # 布局计算服务
│   │   ├── visualization_service.py  # 可视化服务
│   │   ├── transform_service.py # AST转换服务
│   │   └── code_execution_service.py # 代码执行服务
│   ├── utils/                   # 工具模块
│   │   ├── __init__.py
│   │   └── ast_converter.py     # AST转换工具
│   ├── static/                  # 静态文件
│   │   ├── css/                 # CSS样式
│   │   └── js/                  # JavaScript文件
│   ├── templates/               # 模板文件
│   │   └── index.html          # 主页模板
│   └── __init__.py
├── tests/                       # 测试目录
│   ├── unit/                    # 单元测试
│   ├── integration/             # 集成测试
│   └── test_ast_converter.py    # 示例测试
├── config.py                    # 配置文件
├── main.py                      # 新的启动文件
├── app.py                       # 原启动文件（保留）
├── requirements.txt             # 依赖文件
├── run.sh                      # 启动脚本
└── README.md                   # 项目文档
```

## 🏗️ 架构设计

### 模块划分

#### 🎯 Backend (后端核心)

- **app.py**: Flask应用工厂，应用配置和初始化

#### 🌐 API (接口层)

- **controllers.py**: RESTful API端点，处理HTTP请求

#### 📊 Models (数据模型)

- **ast_models.py**: AST节点、位置、可视化属性等数据模型

#### ⚙️ Services (业务逻辑)

- **layout_service.py**: 2D/3D布局算法计算
- **visualization_service.py**: 节点可视化属性管理
- **transform_service.py**: AST转换操作
- **code_execution_service.py**: 安全代码执行

#### 🛠️ Utils (工具模块)

- **ast_converter.py**: AST与字典格式互转

## 🚀 快速开始

### 使用新的启动方式

```bash
# 方式1: 使用新的模块化启动文件
python main.py

# 方式2: 使用原来的启动脚本
./run.sh

# 方式3: 使用原来的启动文件
python app.py
```

### 开发环境设置

```bash
# 1. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
python main.py
```

## 🧪 测试

```bash
# 运行单个测试文件
python tests/test_ast_converter.py

# 运行所有测试（如果有测试框架）
python -m pytest tests/

# 运行特定的测试类
python -m unittest tests.test_ast_converter.TestASTConverter
```

## 🔧 配置管理

项目使用 `config.py` 进行配置管理，支持不同环境：

```python
# 开发环境
export FLASK_ENV=development

# 生产环境  
export FLASK_ENV=production

# 测试环境
export FLASK_ENV=testing
```

## 📡 API接口

### 核心接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/parse` | POST | 解析Python代码为AST |
| `/api/parse_2d` | POST | 解析代码并计算2D布局 |
| `/api/parse_3d` | POST | 解析代码并计算3D布局 |
| `/api/unparse` | POST | 将AST转换回Python代码 |
| `/api/execute` | POST | 执行Python代码 |
| `/api/transform` | POST | 执行AST转换操作 |
| `/api/transforms` | GET | 获取可用转换操作 |
| `/api/validate` | POST | 验证代码语法 |
| `/api/execution-limits` | GET | 获取执行限制信息 |

### 请求示例

```bash
# 解析代码
curl -X POST http://127.0.0.1:5001/api/parse \
  -H "Content-Type: application/json" \
  -d '{"code": "def hello(): print(\"Hello World\")"}'

# 2D可视化
curl -X POST http://127.0.0.1:5001/api/parse_2d \
  -H "Content-Type: application/json" \
  -d '{"code": "def hello(): print(\"Hello\")", "layout": "tree"}'
```

## 🎨 扩展开发

### 添加新的布局算法

1. 在 `LayoutService` 中添加新方法
2. 更新前端布局选择器
3. 添加相应的测试

### 添加新的转换操作

1. 在 `TransformService` 中实现转换逻辑
2. 在 `get_available_transforms()` 中注册
3. 更新API控制器处理逻辑

### 添加新的可视化属性

1. 更新 `VisualProperties` 模型
2. 在 `VisualizationService` 中添加处理逻辑
3. 更新前端渲染代码

## 🔒 安全特性

- **代码执行沙箱**: 限制可用的内置函数
- **执行时间限制**: 防止无限循环
- **代码长度限制**: 防止过大的代码输入
- **输入验证**: 严格的API参数验证

## 🌟 功能特性

### 🔄 双模式可视化

- **2D视图**: SVG-based平面可视化，清晰直观
- **3D视图**: Three.js立体可视化，沉浸体验
- **一键切换**: 无缝在2D/3D模式间切换

### 📐 多种布局算法

- **树形布局**: 经典层次化结构
- **径向布局**: 放射状节点排列
- **网格布局**: 规整的网格排列  
- **螺旋布局**: 3D螺旋空间布局

### 🛠️ AST转换功能

- **函数重命名**: 批量重命名函数和调用
- **日志注入**: 自动添加日志输出
- **常量替换**: 查找替换常量值
- **语句删除**: 按类型删除语句

### 🎯 交互功能

- **节点选择**: 点击查看节点详情
- **属性编辑**: 实时修改节点属性
- **代码执行**: 安全的代码运行环境
- **实时预览**: 即时查看修改结果

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📜 许可证

MIT License - 详见 LICENSE 文件

## 🔄 迁移说明

从单文件版本迁移到模块化版本：

1. **保持兼容**: 原 `app.py` 仍可使用
2. **新启动方式**: 推荐使用 `main.py`
3. **API兼容**: 所有API端点保持不变
4. **功能增强**: 新增配置管理和测试支持
