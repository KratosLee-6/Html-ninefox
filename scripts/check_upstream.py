"""check_upstream.py · Skill 联盟上游巡检（0.9.8，挂月度 cron）

读 data/alliance/*.yaml 的 homepage，用 GitHub API 取 stars / pushed_at /
license，比对 manifest 里的 upstream_* 记账字段，输出差异：
  * 404 / 取不到      → 「死链」——上游没了要人工决策（下架或换源）
  * pushed_at 变新    → 「上游有更新」——能力口径可能过期（baoyu 404 与
                        huashu 落后一个大版本都是人肉记账漏掉的）
  * license 变化      → 「许可变化」——合规红线，最高优先级
  * stars 变化        → 仅提示（口径速朽，不作门禁）

    python -I scripts/check_upstream.py            # 全部成员
    python -I scripts/check_upstream.py guizang    # 名字子串过滤
退出码：死链或许可变化 = 1，其余差异 = 0（差异是提示不是事故）。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
ALLIANCE = ROOT / "htmlninefox" / "data" / "alliance"


def gh_api(path: str, timeout: float = 20.0) -> tuple[int, dict | None]:
    """GitHub API 单次请求（巡检脚本不做重试风暴——失败如实报，月度再跑）。"""
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "htmlninefox-upstream-check"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, None
    except Exception as error:  # noqa: BLE001
        print(f"  [network] {error.__class__.__name__}: {error}")
        return 0, None


def parse_homepage(homepage: str) -> str | None:
    """homepage → github api repo path（仅支持 github.com 链接）。"""
    marker = "github.com/"
    if marker not in homepage:
        return None
    tail = homepage.split(marker, 1)[1].strip("/")
    parts = [p for p in tail.split("/") if p]
    if len(parts) < 2:
        return None
    return f"/repos/{parts[0]}/{parts[1]}"


def main() -> int:
    needle = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
    manifests = sorted(p for p in ALLIANCE.glob("*.yaml") if needle in p.name.lower())
    if not manifests:
        print("没有匹配的联盟成员")
        return 1
    hard = False
    for path in manifests:
        name = path.stem
        homepage = ""
        recorded: dict = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("homepage:"):
                homepage = line.split(":", 1)[1].strip()
            if line.startswith("upstream_"):
                key, _, value = line.partition(":")
                recorded[key.strip()] = value.strip()
        repo = parse_homepage(homepage)
        print(f"\n== {name} ({homepage or '无 homepage'})")
        if repo is None:
            print("  [skip] homepage 不是 github.com 仓库链接，跳过 API 巡检")
            continue
        status, data = gh_api(repo)
        if status == 404:
            print("  [死链] 仓库 404 —— 上游已消失，需人工决策下架或换源")
            hard = True
            continue
        if status != 200 or not data:
            print(f"  [network] GitHub API status={status}，本月跳过（下月再查）")
            continue
        pushed = str(data.get("pushed_at", ""))[:10]
        license_id = ((data.get("license") or {}).get("spdx_id")) or "unknown"
        stars = data.get("stargazers_count")
        rec_license = str(recorded.get("upstream_license", ""))
        rec_date = str(recorded.get("upstream_checked_at", ""))
        lic_hit = license_id and license_id != "unknown" and license_id not in rec_license
        print(f"  stars: {stars}   pushed_at: {pushed}   license: {license_id}")
        print(f"  记账:   checked_at={rec_date or '—'}   license≈{rec_license or '—'}")
        if lic_hit:
            print(f"  [许可变化] 上游现在标 {license_id}，与记账 {rec_license} 不一致 —— "
                  "合规红线，先停接入再评估")
            hard = True
        if rec_date and pushed > rec_date:
            print("  [上游有更新] pushed_at 晚于记账日期 —— 能力口径可能过期，"
                  "建议重读 README 并更新 upstream_* 字段")
    print("\n== 巡检结束；死链/许可变化为硬问题（退出码 1），其余为提示 ==")
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
