"""动效质量门禁（v0.8.7 接入 motion-design-skill，评估见 docs/EVAL-motion-design-skill-20261101.md）。

规则源自 LottieFiles/motion-design-skill（MIT）的 CRITICAL 质量律与时长表，
自研实现并注明来源；「只禁变差」纪律沿用——下列不变量今天全部成立，
门禁的价值是拦住未来的回归：

  * 时长 token 对齐元素类型表（tooltip 80-120 / 按压 120-180 / 图标 150-250 / 卡片 200-350）；
  * 入场 > 退场（用户在意出现的东西）；重量递增（轻 ≤ 中 ≤ 重）；
  * CRITICAL #1：空间位移禁止 linear 缓动——白名单仅 spinner/progress（skill 原文同款例外）；
  * CRITICAL #2：显形不得 opacity-only——必须伴随 transform；
  * 编排预算：stagger 总预算 < 500ms；戏剧性显式揭示 ∈ 600-1200ms；
  * 环境循环必须 ease-in-out/sine（无缝循环禁 linear/过冲）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STATIC = ROOT / "htmlninefox" / "server" / "static"
SHARED = ROOT / "htmlninefox" / "generators" / "_shared.py"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _motion_tokens() -> dict[str, int]:
    """从 motion-system.js 的 root 注入行解析 --motion-*:NNms。"""
    js = _read(STATIC / "motion-system.js")
    tokens = {name: int(ms) for name, ms in
              re.findall(r"--motion-([a-z]+):(\d+)ms", js)}
    assert tokens, "motion-system.js 里一个时长 token 都没扫到，正则可能失效"
    return tokens


def test_duration_tokens_match_element_type_table():
    tokens = _motion_tokens()
    # 元素类型表（motion-design-skill Duration Table）
    assert 80 <= tokens["instant"] <= 120, tokens   # tooltip / 微反馈
    assert 120 <= tokens["feedback"] <= 180, tokens  # 按压 / 开关
    assert 150 <= tokens["enter"] <= 250, tokens     # 图标过渡
    assert 200 <= tokens["panel"] <= 350, tokens     # 卡片进出场
    # 入场 > 退场（Enter > Exit 规则）；重量递增（轻 ≤ 中 ≤ 重）
    assert tokens["enter"] > tokens["exit"], tokens
    assert tokens["instant"] <= tokens["feedback"] <= tokens["enter"] <= tokens["panel"], tokens


def test_no_linear_easing_for_spatial_movement():
    """CRITICAL #1：linear 只留给 spinner/progress——空间位移必须有缓动。"""
    allowed = re.compile(r"spin|progress|marquee", re.IGNORECASE)
    offenders: list[str] = []
    files = list(STATIC.glob("*.css")) + [STATIC / "motion-system.js", SHARED]
    for path in files:
        if not path.is_file():
            continue
        for line_no, line in enumerate(
                _read(path).splitlines(), start=1):
            if "linear-gradient" in line:
                continue
            for declaration in re.findall(
                    r"(?:animation|transition):[^;{}]+", line):
                if not re.search(r"(?<![-\w])linear(?![\w-])", declaration):
                    continue
                if allowed.search(declaration):
                    continue
                offenders.append(f"{path.name}:{line_no} {declaration.strip()}")
    assert not offenders, (
        f"空间位移用了 linear 缓动（动效导演规则：linear 仅限 spinner/progress）：{offenders}")


def test_reveal_accompanies_transform_and_stays_in_budget():
    """CRITICAL #2 + 编排预算：显形入场的 transition 必须写在 after-change 态
    （.fox-in）且同时携带 opacity+transform，cap < 500ms。

    历史教训（0.8.7 实锤）：transition 写在 .fox-reveal 基类时，被同特异性的
    .card 交互 transition 整体覆盖——0.6s 编排静默死亡，显形退化瞬切
    （浏览器采样 opacity 时间线：0→1 不足 100ms）。after-change 态规则
    天然免疫后续覆盖。入场完成后 .fox-done 切回 .18s 交互档保 hover 响应。"""
    shared = _read(SHARED)
    fox_in = re.search(r"\.fox-reveal\.fox-in \{(.*?)\}", shared, re.S)
    assert fox_in, "找不到 .fox-reveal.fox-in 块——显形结构变了？"
    transition = re.search(r"transition:([^;]+);", fox_in.group(1))
    assert transition, "fox-in 态没有 transition——显形会退化为瞬切"
    props = transition.group(1)
    assert "opacity" in props and "transform" in props, (
        f"fox-in 的 transition 退化为 opacity-only（CRITICAL #2）：{props.strip()}")
    assert ".6s" in props, "入场编排不再是 .6s——电影感丢失"
    done = re.search(r"\.fox-reveal\.fox-done \{([^}]+)\}", shared)
    assert done and ".18s" in done.group(1), (
        "缺少 .fox-done 交互档——入场后 hover 会拖到 .6s（响应性丢失）")
    caps = [int(v) for v in re.findall(r"Math\.min\((\d+)", shared)]
    assert caps and max(caps) < 500, (
        f"stagger cap 超出 500ms 总预算：{caps}")


def test_ink_in_is_a_dramatic_reveal_not_a_page_load():
    """墨水标题 700ms ∈ 戏剧性揭示档（600-1200ms）——再快就丢失仪式感。"""
    shared = _read(SHARED)
    match = re.search(r"fox-ink-drop\s+([\d.]+)s", shared)
    assert match, "找不到 fox-ink-drop 时长"
    ms = float(match.group(1)) * 1000
    assert 600 <= ms <= 1200, f"ink-in {ms}ms 落在戏剧档之外"


def test_ambient_loops_are_seamless_not_linear():
    """环境循环走向规则：ease-in-out/sine——linear 循环看着像传送带。"""
    shared = _read(SHARED)
    ambient = re.search(r"animation:\s*fox-ambient-drift\s+([^;]+);", shared)
    assert ambient, "找不到 fox-ambient-drift 声明"
    timing = ambient.group(1)
    assert "linear" not in timing and ("ease-in-out" in timing or "sine" in timing), timing
