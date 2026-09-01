#!/usr/bin/env bash
set -euo pipefail

PROMPT="做一个深色 API 监控数据看板，展示延迟、错误率、请求量和可用性"
python -m htmlninefox expert "$PROMPT" --type dashboard --template shadcn-dashboard --quiet-llm --output ./output
echo "已生成到 ./output/html9n-*/output.html"
