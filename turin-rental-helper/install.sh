#!/bin/bash

# 都灵租房助手 - 安装脚本

set -e

echo "=========================================="
echo "都灵租房助手 (Turin Rental Helper) 安装"
echo "=========================================="
echo

# 检查Python版本
echo "检查Python版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.7.0"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✓ Python版本: $python_version"
else
    echo "✗ Python版本过低: $python_version (需要 3.7+)"
    exit 1
fi

# 安装依赖
echo
echo "安装Python依赖..."
if [ -f "requirements.txt" ]; then
    # 检查是否在conda环境中
    if [ -n "$CONDA_DEFAULT_ENV" ]; then
        echo "检测到Conda环境: $CONDA_DEFAULT_ENV"
        pip install -r requirements.txt
    else
        pip3 install -r requirements.txt
    fi
    echo "✓ 依赖安装完成"
else
    echo "✓ 无需额外依赖（使用标准库）"
fi

# 验证numpy安装
echo
echo "验证numpy安装..."
if python3 -c "import numpy; print(f'numpy版本: {numpy.__version__}')" 2>/dev/null; then
    echo "✓ numpy已安装"
else
    echo "⚠ numpy未安装，正在安装..."
    pip3 install numpy>=1.21.0
    echo "✓ numpy安装完成"
fi

# 检查Claude Code
echo
echo "检查Claude Code..."
if command -v claude &> /dev/null; then
    echo "✓ Claude Code 已安装"
else
    echo "⚠ Claude Code 未安装"
    echo "  请访问 https://claude.ai/code 安装Claude Code"
fi

# 创建skill目录
echo
echo "安装skill..."
SKILL_DIR="$HOME/.claude/skills/turin-rental-helper"

if [ -d "$SKILL_DIR" ]; then
    echo "⚠ skill目录已存在: $SKILL_DIR"
    read -p "是否覆盖？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$SKILL_DIR"
        cp -r "$(dirname "$0")" "$SKILL_DIR"
        echo "✓ skill已更新"
    else
        echo "跳过skill安装"
    fi
else
    mkdir -p "$HOME/.claude/skills"
    cp -r "$(dirname "$0")" "$SKILL_DIR"
    echo "✓ skill已安装到: $SKILL_DIR"
fi

echo
echo "=========================================="
echo "安装完成！"
echo "=========================================="
echo
echo "使用方法："
echo "  1. 启动 Claude Code"
echo "  2. 输入找房需求，例如："
echo "     '我即将去都灵留学，想找一个靠近都灵理工大学的单间公寓'"
echo
echo "更多信息请参考 README.md"
echo
