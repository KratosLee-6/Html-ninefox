#!/usr/bin/env bash
# expert_dashboard.sh — Generate an API monitoring dashboard using Html九尾狐
#
# Usage:
#   chmod +x examples/expert_dashboard.sh
#   ./examples/expert_dashboard.sh
#
# What this does:
#   1. Runs the full 5-agent pipeline on an internal-tool dashboard Brief
#   2. Uses brutalist style (data density)
#   3. Renders to output/dashboard.html

set -euo pipefail

# --- Configuration ---
BRIEF="${BRIEF:-examples/briefs/api_dashboard.txt}"
STYLE="${STYLE:-brutalist}"
OUTPUT="${OUTPUT:-output/dashboard.html}"

# --- Colors ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# --- Pre-flight ---
echo -e "${BLUE}🦊 Html九尾狐 · Expert CLI · Dashboard Demo${NC}"
echo "=========================================="
echo ""

if [[ ! -f "$BRIEF" ]]; then
    echo -e "${RED}❌ Brief not found: $BRIEF${NC}"
    echo "Using default brief content instead..."

    # Create a minimal brief if file doesn't exist
    mkdir -p "$(dirname "$BRIEF")"
    cat > "$BRIEF" <<'EOF'
Product: API Health Dashboard
Audience: SRE team, internal tool
Goal: Spot incidents fast (p99 latency, error rate)
Style hint: data-dense, dark mode preferred
Tone: technical, no marketing fluff
Assets: status icons, sparkline placeholders
Constraints: real-time refresh, print-friendly fallback
EOF
    echo -e "${GREEN}✅ Created default brief: $BRIEF${NC}"
fi

mkdir -p "$(dirname "$OUTPUT")"

# --- Run ---
echo -e "${YELLOW}📋 Brief: $BRIEF${NC}"
echo -e "${YELLOW}🎨 Style: $STYLE (best for data density)${NC}"
echo -e "${YELLOW}📤 Output: $OUTPUT${NC}"
echo ""

echo -e "${BLUE}Running 5-agent pipeline (brutalist style)...${NC}"
echo ""

python -m fox.cli expert \
    --brief "$BRIEF" \
    --style "$STYLE" \
    --output "$OUTPUT"

EXIT_CODE=$?

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✅ Dashboard generated!${NC}"
    echo ""
    echo "Expected output:"
    echo "  - 4 KPI cards (latency, error rate, RPS, uptime)"
    echo "  - 2 chart placeholders (latency trend, error distribution)"
    echo "  - Log tail (last 10 entries)"
    echo ""
    echo "Open: $OUTPUT"
else
    echo -e "${RED}❌ CLI failed (exit $EXIT_CODE)${NC}"
    exit $EXIT_CODE
fi
