#!/usr/bin/env bash
set -euo pipefail

# 一键批量处理脚本
# 用法示例：
# ./run_all.sh ./videos ./batch_out 1 16:9 15 "国风武侠："

INPUT_DIR="${1:-./videos}"
OUTPUT_DIR="${2:-./batch_out}"
FPS="${3:-1}"
RATIO="${4:-16:9}"
DURATION="${5:-15}"
TOPIC_PREFIX="${6:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "$INPUT_DIR" ]; then
  echo "❌ 输入目录不存在: $INPUT_DIR"
  echo "用法: ./run_all.sh [input_dir] [output_dir] [fps] [ratio] [duration] [topic_prefix]"
  exit 1
fi

echo "🚀 开始批量处理"
echo "- 输入目录: $INPUT_DIR"
echo "- 输出目录: $OUTPUT_DIR"
echo "- 抽帧FPS: $FPS"
echo "- 比例: $RATIO"
echo "- 时长: $DURATION"
if [ -n "$TOPIC_PREFIX" ]; then
  echo "- 主题前缀: $TOPIC_PREFIX"
fi

python batch_seedance_export.py \
  --input-dir "$INPUT_DIR" \
  --output-dir "$OUTPUT_DIR" \
  --fps "$FPS" \
  --ratio "$RATIO" \
  --duration "$DURATION" \
  ${TOPIC_PREFIX:+--topic-prefix "$TOPIC_PREFIX"}

echo "✅ 全部完成"
echo "输出目录: $OUTPUT_DIR"
