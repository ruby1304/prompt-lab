#!/bin/bash

# 演示新的统一评估命令的使用方法

echo "=== 新的统一评估命令演示 ==="
echo

echo "1. 单个flow执行（不带judge）："
echo "python -m src eval --agent mem0_l1_summarizer --flows mem0_l1_v3 --limit 3"
echo

echo "2. 单个flow执行（带judge评估）："
echo "python -m src eval --agent mem0_l1_summarizer --flows mem0_l1_v3 --judge --limit 3"
echo

echo "3. 多个flow对比执行（不带judge）："
echo "python -m src eval --agent mem0_l1_summarizer --flows mem0_l1_v1,mem0_l1_v2,mem0_l1_v3 --limit 3"
echo

echo "4. 多个flow对比执行（带judge评估）："
echo "python -m src eval --agent mem0_l1_summarizer --flows mem0_l1_v1,mem0_l1_v2,mem0_l1_v3 --judge --limit 3"
echo

echo "5. 使用agent的所有flows（带judge评估）："
echo "python -m src eval --agent mem0_l1_summarizer --judge --limit 3"
echo

echo "=== 优势 ==="
echo "✅ 一个命令完成执行+评估"
echo "✅ 自动生成带时间戳的文件名"
echo "✅ 统一的token统计和结果展示"
echo "✅ 支持单flow和多flow对比"
echo "✅ 可选择是否立即进行judge评估"
echo

echo "要运行演示，请选择上面的命令之一执行。"