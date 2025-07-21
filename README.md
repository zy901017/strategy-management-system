# 负成本持仓策略管理系统 - Render专用版

## 🚀 Render部署版特点

这是专门为Render平台优化的负成本持仓策略管理系统，包含所有核心功能：

### ✅ 核心功能

- **负成本策略算法** - 智能计算负成本持仓可能性
- **交易记录管理** - 完整的买卖历史追踪
- **资金管理系统** - 智能资金分配策略
- **风险评估工具** - 多维度风险分析
- **投资建议引擎** - AI驱动的买卖时机建议

### ✅ Render优化

- **持久化存储** - 使用Render磁盘卷保存数据
- **自动部署** - 支持GitHub自动部署
- **环境适配** - 完全兼容Render环境
- **健康检查** - 内置健康检查端点

## 🔧 文件结构

```
Render_Deploy/
├── app.py              # 主应用文件
├── render.yaml         # Render配置文件
├── requirements.txt    # 依赖文件
├── data/               # 数据目录
│   └── strategy.db     # SQLite数据库
├── static/             # 静态资源
│   ├── css/            # 样式文件
│   └── js/             # JavaScript文件
├── templates/          # HTML模板
│   ├── base.html       # 基础模板
│   ├── index.html      # 首页
│   ├── add_stock.html  # 添加股票
│   ├── edit_stock.html # 编辑股票
│   ├── trades.html     # 交易记录
│   ├── strategy.html   # 策略分析
│   └── fund_management.html # 资金管理
└── README.md           # 说明文件
```

## 📋 部署步骤

1. **创建Render账户**：访问 https://render.com 并注册
2. **创建新Web服务**：点击"New" → "Web Service"
3. **连接GitHub**：选择包含此代码的GitHub仓库
4. **配置服务**：
   - **Name**: strategy-management-system
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. **创建磁盘卷**（可选但推荐）：
   - 点击"Disks"标签
   - 添加新磁盘卷
   - 挂载路径：`/var/data`
   - 设置环境变量：`RENDER_EXTERNAL_VOLUME=/var/data`
6. **部署**：点击"Create Web Service"

## 🎯 功能说明

### 首页 (`/`)
- 投资组合总览
- 实时盈亏统计
- 各股票策略分析

### 添加股票 (`/add_stock`)
- 股票基本信息录入
- 初始投资金额设置
- 目标持仓配置

### 策略分析 (`/strategy/<code>`)
- 单只股票详细分析
- 负成本策略建议
- 具体操作步骤

### 交易记录 (`/trades`)
- 历史交易查看
- 交易记录添加
- 成本基础更新

### 资金管理 (`/fund_management`)
- 总资金配置
- 可用资金管理
- 复利再投资设置

## 🔍 API端点

- `/api/stocks` - 获取所有股票信息
- `/api/strategy/<code>` - 获取单只股票策略分析
- `/health` - 系统健康检查

## 🎉 部署成功后

访问您的Render应用URL（格式：`https://your-app-name.onrender.com`）即可开始使用！

## 📊 示例数据

系统会自动初始化数据库，您可以立即添加股票并开始使用。

## 🔒 数据安全

所有数据存储在Render磁盘卷中，定期备份以确保数据安全。

