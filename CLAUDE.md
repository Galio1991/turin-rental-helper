# 都灵租房助手 (Turin Rental Helper)

## 项目概述

为前往意大利都灵留学的中国学生提供个性化租房服务的 Claude Code Skill。

## 功能特性

- 智能需求收集
- 多源数据采集（Immobiliare.it、Idealista.it等）
- 多维度分析（价格、位置、设施、安全）
- 个性化推荐
- 综合输出（对比表格、详细报告、看房清单）

## 环境依赖

### 系统要求

- Python 3.7+
- Claude Code CLI

### Python 依赖

```bash
pip install -r requirements.txt
```

**注意**: 核心模块仅使用 Python 标准库。

### Claude Code 依赖

- **Firecrawl** (可选) - 用于网页爬取
- **WebSearch** (可选) - 用于搜索补充信息

## 安装

```bash
git clone https://github.com/你的用户名/turin-rental-helper.git
cd turin-rental-helper
pip install -r requirements.txt
cp -r turin-rental-helper ~/.claude/skills/
```

## 使用方法

### 触发条件

当用户提到以下关键词时自动触发：
- 都灵租房、都灵找房、Turin rental
- 意大利租房、留学住房
- Immobiliare、Idealista

### 使用示例

```
用户: 我即将去都灵留学，想找一个靠近都灵理工大学的单间公寓，预算500欧以内
助手: 我来帮你找都灵的房子！首先让我了解一些你的具体需求...
```

## 项目结构

```
turin-rental-helper/
├── SKILL.md                    # 主skill文档
├── README.md                   # 使用说明
├── requirements.txt            # Python依赖
├── scripts/                    # Python脚本
├── references/                 # 参考文档
├── assets/                     # 资源文件
└── evals/                      # 测试用例
```

## 核心模块

### 脚本说明

| 脚本 | 功能 |
|------|------|
| `requirements_collector.py` | 交互式收集用户需求 |
| `scraper.py` | 爬取房源信息 |
| `analyzer.py` | 多维度数据分析 |
| `comparator.py` | 房源对比推荐 |
| `report_generator.py` | 生成各类报告 |

### 参考文档

| 文档 | 内容 |
|------|------|
| `turin-districts.md` | 都灵13个主要区域详细介绍 |
| `rental-contract.md` | 意大利租房合同完全指南 |
| `cost-analysis.md` | 费用构成和预算规划 |
| `university-locations.md` | 6所主要大学位置和交通 |

## 特色功能

### 智能费用分析

- 区分集中供暖vs独立供暖
- 解析费用明细（水费、物业费、供暖费）
- 计算年度总成本
- 识别隐藏费用

### 多维度评估

- 价格分析（性价比、区域均价对比）
- 位置分析（学校距离、交通便利性）
- 设施分析（暖气、空调、家具）
- 安全评估（区域治安、夜间安全）

## 开发指南

### 代码风格

- 使用 Python 3.7+ 语法
- 遵循 PEP 8 规范
- 添加类型注解
- 编写文档字符串

### 提交规范

```
feat: 添加新功能
fix: 修复问题
docs: 更新文档
style: 代码格式调整
refactor: 重构代码
test: 添加测试
```

## 许可证

MIT License
