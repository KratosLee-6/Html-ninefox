#!/usr/bin/env bash
set -euo pipefail

python -m htmlninefox expert "做一个 SaaS 落地页，品牌狐构" --type landing --quiet-llm --output ./output
PROJECT=$(ls -dt output/html9n-* | head -1)
python -m htmlninefox feedback --project "$PROJECT" --note "颜色再深一点，标题大一点"
echo "最新项目：$PROJECT"
