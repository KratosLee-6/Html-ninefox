#!/usr/bin/env bash
set -euo pipefail

python -m htmlninefox expert "做一个 SaaS 落地页，主推 AI 创作工具，目标用户是设计师" --type landing --quiet-llm --output ./output
echo "打开 ./output/html9n-*/output.html 查看结果"
