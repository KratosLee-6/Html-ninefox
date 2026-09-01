#!/usr/bin/env bash
set -euo pipefail

PROMPT="做一个 SaaS 落地页，品牌狐构，主推 AI 创作工具，目标用户是设计师"
python -m htmlninefox expert "$PROMPT" --type landing --quiet-llm --output ./output
echo "已生成到 ./output/html9n-*/output.html"
