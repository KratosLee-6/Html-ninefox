#!/usr/bin/env bash
# feedback_iteration.sh — Demo of Html九尾狐's feedback-loop iteration
#
# Usage:
#   chmod +x examples/feedback_iteration.sh
#   ./examples/feedback_iteration.sh
#
# What this does:
#   1. Runs the pipeline once, captures feedback score
#   2. If score < 0.8, re-runs with iteration
#   3. Shows the score progression across iterations

set -euo pipefail

# --- Configuration ---
BRIEF="${BRIEF:-examples/briefs/saas_landing.txt}"
STYLE="${STYLE:-swiss}"
OUTPUT="${OUTPUT:-output/landing.html}"
TARGET_SCORE="${TARGET_SCORE:-0.85}"
MAX_ITER="${MAX_ITER:-3}"

# --- Colors ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# --- Header ---
echo -e "${BLUE}🦊 Html九尾狐 · Feedback Iteration Demo${NC}"
echo "=========================================="
echo ""
echo -e "${YELLOW}Target score: $TARGET_SCORE${NC}"
echo -e "${YELLOW}Max iterations: $MAX_ITER${NC}"
echo ""

# --- Initial run ---
ITER=0
LATEST_SCORE=0.0

while [[ $ITER -lt $MAX_ITER ]]; do
    ITER=$((ITER + 1))
    echo -e "${BLUE}━━━ Iteration $ITER / $MAX_ITER ━━━${NC}"

    # Run with iteration enabled for subsequent runs
    if [[ $ITER -gt 1 ]]; then
        python -m fox.cli expert \
            --brief "$BRIEF" \
            --style "$STYLE" \
            --output "$OUTPUT" \
            --iterate \
            --max-iter 1 \
            --feedback-prev "output/feedback.json"
    else
        python -m fox.cli expert \
            --brief "$BRIEF" \
            --style "$STYLE" \
            --output "$OUTPUT"
    fi

    # Read feedback score
    if [[ -f "output/feedback.json" ]]; then
        LATEST_SCORE=$(python -c "
import json, sys
with open('output/feedback.json') as f:
    data = json.load(f)
print(data.get('score', 0.0))
")
        echo -e "${YELLOW}📊 Score: $LATEST_SCORE${NC}"

        # Compare with target
        IS_GOOD=$(python -c "print(1 if $LATEST_SCORE >= $TARGET_SCORE else 0)")
        if [[ "$IS_GOOD" == "1" ]]; then
            echo -e "${GREEN}✅ Score >= $TARGET_SCORE — done!${NC}"
            break
        else
            echo -e "${YELLOW}⚠️  Score < $TARGET_SCORE, iterating...${NC}"
        fi
    else
        echo -e "${RED}❌ No feedback.json produced${NC}"
        exit 1
    fi

    echo ""
done

echo ""
echo "=========================================="
if (( $(echo "$LATEST_SCORE >= $TARGET_SCORE" | python -c "import sys; print(1 if sys.stdin.read().strip() == 'True' else 0)") )); then
    echo -e "${GREEN}🎉 Final score: $LATEST_SCORE (target: $TARGET_SCORE)${NC}"
else
    echo -e "${YELLOW}⚠️  Final score: $LATEST_SCORE (target: $TARGET_SCORE)${NC}"
    echo "Consider editing the Brief to address the issues in feedback.json"
fi
echo ""
echo "Output: $OUTPUT"
echo "Feedback: output/feedback.json"
