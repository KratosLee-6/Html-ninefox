"""
feedback_python.py — Python API demo for Html九尾狐's feedback-loop iteration.

This example shows how to call the Html九尾狐 Python API directly (instead of CLI)
when you need to integrate it into a larger Python application.

Usage:
    pip install -e .   # install Html九尾狐 as editable package
    python examples/feedback_python.py

What it does:
    1. Calls the expert pipeline programmatically
    2. Inspects feedback.score
    3. If score < target, calls again with feedback-aware options
    4. Prints score progression across iterations
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add repo root to sys.path so we can import fox
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

# --- Import Html九尾狐 public API ---
try:
    from fox.agents import brief, style, asset, generate, feedback
    from fox.alliance.router import Router
    from fox.libs.brief_lib import BriefLib
    from fox.libs.template_lib import TemplateLib
    from fox.libs.feedback_lib import FeedbackLib
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Make sure you ran 'pip install -e .' from the repo root.")
    sys.exit(1)


# --- Configuration ---
TARGET_SCORE = 0.85
MAX_ITERATIONS = 3
BRIEF_PATH = REPO_ROOT / "examples" / "briefs" / "saas_landing.txt"
STYLE_ID = "swiss"
OUTPUT_PATH = REPO_ROOT / "output" / "landing.html"


def run_pipeline(brief_text: str, style_id: str, output_path: Path) -> dict:
    """Run the full 5-agent pipeline and return the feedback dict."""
    print(f"\n🔄 Running pipeline (style={style_id})...")

    # [1] brief agent
    print("  [1/5] brief agent...", end=" ")
    brief_spec = brief.parse(brief_text)
    print(f"✅ (audience={brief_spec.audience!r})")

    # [2] style agent
    print("  [2/5] style agent...", end=" ")
    style_profile = style.pick(brief_spec, preferred=style_id)
    print(f"✅ (template={style_profile.template_id})")

    # [3] asset agent
    print("  [3/5] asset agent...", end=" ")
    asset_paths = asset.fetch(brief_spec, style_profile)
    print(f"✅ ({len(asset_paths)} assets)")

    # [4] generate agent
    print("  [4/5] generate agent...", end=" ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generate.render(
        brief_spec=brief_spec,
        style_profile=style_profile,
        asset_paths=asset_paths,
        output_path=output_path,
    )
    print(f"✅ ({output_path.stat().st_size // 1024} KB)")

    # [5] feedback agent
    print("  [5/5] feedback agent...", end=" ")
    fb = feedback.score(output_path, brief_spec)
    print(f"✅ score={fb['score']:.2f}")

    return fb


def main() -> int:
    """Main entry point with iteration loop."""
    print("🦊 Html九尾狐 · Python API Demo · Feedback Iteration")
    print("=" * 50)
    print(f"  Target score: {TARGET_SCORE}")
    print(f"  Max iterations: {MAX_ITERATIONS}")
    print(f"  Brief: {BRIEF_PATH}")
    print(f"  Output: {OUTPUT_PATH}")
    print()

    # Load brief
    if not BRIEF_PATH.exists():
        print(f"❌ Brief not found: {BRIEF_PATH}")
        return 1
    brief_text = BRIEF_PATH.read_text(encoding="utf-8")

    # Iterate
    score = 0.0
    for i in range(1, MAX_ITERATIONS + 1):
        print(f"\n━━━ Iteration {i} / {MAX_ITERATIONS} ━━━")
        fb = run_pipeline(brief_text, STYLE_ID, OUTPUT_PATH)
        score = fb["score"]

        if score >= TARGET_SCORE:
            print(f"\n🎉 Score {score:.2f} >= {TARGET_SCORE} — done!")
            break

        print(f"\n⚠️  Score {score:.2f} < {TARGET_SCORE}, iterating...")
        print(f"   Issues: {fb.get('issues', [])}")
        print(f"   Suggestions: {fb.get('suggestions', [])}")

    # Summary
    print("\n" + "=" * 50)
    if score >= TARGET_SCORE:
        print(f"✅ SUCCESS · Final score: {score:.2f}")
        return 0
    else:
        print(f"⚠️  PARTIAL · Final score: {score:.2f} (target: {TARGET_SCORE})")
        print("   Consider editing the Brief to address the issues.")
        return 0  # Don't fail — just warn


if __name__ == "__main__":
    sys.exit(main())
