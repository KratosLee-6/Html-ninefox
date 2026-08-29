#!/usr/bin/env bash
# expert_landing.sh — Generate a SaaS landing page using Html九尾狐 expert CLI
#
# Usage:
#   chmod +x examples/expert_landing.sh
#   ./examples/expert_landing.sh
#
# What this does:
#   1. Runs the full 5-agent pipeline on a SaaS landing Brief
#   2. Renders to output/landing.html
#   3. Prints the feedback score
#
# Requirements:
#   - Python 3.11+
#   - pip install -r requirements.txt
#   - Working dir: repo root (this script assumes ../)

set -euo pipefail

# --- Configuration ---
BRIEF="${BRIEF:-examples/briefs/saas_landing.txt}"
STYLE="${STYLE:-swiss}"
OUTPUT="${OUTPUT:-output/landing.html}"
ITERATE="${ITERATE:-false}"
MAX_ITER="${MAX_ITER:-3}"

# --- Colors for output ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# --- Pre-flight checks ---
echo -e "${BLUE}🦊 Html九尾狐 · Expert CLI · SaaS Landing Demo${NC}"
echo "=========================================="
echo ""

if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ python not found. Install Python 3.11+ first.${NC}"
    exit 1
fi

if [[ ! -f "$BRIEF" ]]; then
    echo -e "${RED}❌ Brief file not found: $BRIEF${NC}"
    echo "   Available briefs:"
    ls -1 examples/briefs/ 2>/dev/null || echo "   (none found)"
    exit 1
fi

# --- Ensure output dir exists ---
mkdir -p "$(dirname "$OUTPUT")"

# --- Run expert CLI ---
echo -e "${YELLOW}📋 Brief: $BRIEF${NC}"
echo -e "${YELLOW}🎨 Style: $STYLE${NC}"
echo -e "${YELLOW}📤 Output: $OUTPUT${NC}"
echo ""

ITER_FLAG=""
if [[ "$ITERATE" == "true" ]]; then
    ITER_FLAG="--iterate --max-iter $MAX_ITER"
    echo -e "${YELLOW}🔁 Iterate mode: up to $MAX_ITER rounds${NC}"
fi

echo -e "${BLUE}Running 5-agent pipeline...${NC}"
echo ""

python -m fox.cli expert \
    --brief "$BRIEF" \
    --style "$STYLE" \
    --output "$OUTPUT" \
    $ITER_FLAG

EXIT_CODE=$?

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✅ Landing page generated successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Open $OUTPUT in your browser"
    echo "  2. Check output/feedback.json for the score"
    echo "  3. If score < 0.8, re-run with ITERATE=true"
    echo ""
    echo "Open command:"
    echo "  macOS:  open $OUTPUT"
    echo "  Linux:  xdg-open $OUTPUT"
    echo "  Windows: start $OUTPUT"
else
    echo -e "${RED}❌ CLI failed with exit code $EXIT_CODE${NC}"
    exit $EXIT_CODE
fi
