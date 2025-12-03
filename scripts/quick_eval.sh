#!/bin/bash

# LLM-as-Judge 快速评估脚本 (使用新的统一评估命令)
# 用法: ./scripts/quick_eval.sh <agent_name> [sample_size]

set -e

AGENT_NAME=${1:-"mem0_l1_summarizer"}
SAMPLE_SIZE=${2:-10}

echo "🚀 开始 LLM-as-Judge 评估流程 (统一命令版本)"
echo "Agent: $AGENT_NAME"
echo "样本数: $SAMPLE_SIZE"
echo ""

# 使用新的统一评估命令，一步完成执行+评估
echo "🤖 执行统一评估 (包含对比执行和LLM评估)..."
python -m src eval \
  --agent "$AGENT_NAME" \
  --judge \
  --limit "$SAMPLE_SIZE"

if [ $? -ne 0 ]; then
    echo "❌ 统一评估失败"
    exit 1
fi

echo ""
echo "🎉 评估完成！"
echo ""
echo "📁 生成的文件已自动保存到 data/ 目录，文件名包含时间戳"
echo ""
echo "💡 下一步建议:"
echo "  1. 查看生成的 .judge.csv 文件，分析评估结果"
echo "  2. 对比不同flow的性能差异"
echo "  3. 分析各维度得分，找出改进方向"
echo "  4. 基于结果优化 prompt"
echo "  5. 重新评估验证改进效果"
echo ""
echo "🔍 如需详细分析，可运行:"
echo "  python src/analyze_eval_results.py data/<生成的judge文件名> --details"