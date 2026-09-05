"""cli.py · Click CLI 入口（Html九尾狐跨平台工作台）

子命令：
  expert    一句话生成 HTML（5 内容类型 × 6 风格预设 × 联盟路由）
  feedback  反馈迭代（--revise 真实改写 output.html）
  brief     Brief 库管理（list / show / add）
  template  审美模板库（list）
  alliance  Skill 联盟（list）
  app       一键启动工作台并打开浏览器
  workbench 启动 Web 工作台（v0.4，默认 0.0.0.0，便于 Docker/LAN）
  serve     仅启动本地 REST API + UI 服务
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from . import pipeline
from .alliance.router import AllianceRouter
from .libraries import brief_lib, feedback_lib

console = Console()
console_err = Console(stderr=True)


@click.group(help=f"Html九尾狐 · HTML 创作工作台（v{__version__}）")
@click.version_option(__version__, prog_name="htmlninefox")
def main():
    """Html九尾狐 CLI 入口。"""


# ============================================================
# 1. expert
# ============================================================
@main.command()
@click.argument("prompt")
@click.option("--skill", default=None, help="指定联盟 skill（如 guizang-ppt）")
@click.option("--template", default=None, help="使用风格预设 ID（见 template list）")
@click.option("--type", "intent", default=None, type=click.Choice(
    ["landing", "dashboard", "deck", "poster", "archdoc", "doc"]), help="强制内容类型（默认自动路由）")
@click.option("--output", "-o", default="./output", help="输出根目录")
@click.option("--quiet-llm", is_flag=True, help="跳过 LLM 微调，纯离线规则")
def expert(prompt: str, skill: str | None, template: str | None, intent: str | None,
           output: str, quiet_llm: bool):
    """一句话生成可发布的单文件 HTML（offline 也能跑）。"""
    if not prompt.strip():
        console_err.print("[red]✗ prompt 不能为空[/red]")
        sys.exit(2)

    with console.status("[bold cyan]🦊 Html九尾狐 流水线执行中…[/bold cyan]"):
        result = pipeline.run_expert(prompt, skill=skill, template=template,
                                     output=output, intent_override=intent,
                                     quiet_llm=quiet_llm)

    work = result["work"]
    console.print(f"\n[bold cyan]🦊 Html九尾狐 v{__version__}[/bold cyan]  生成完成")
    table = Table(show_header=True, header_style="bold cyan", title="生成结果")
    table.add_column("项", style="green")
    table.add_column("值", style="white")
    table.add_row("内容类型", result["intent"])
    table.add_row("风格预设", f"{result['preset_id']}（{result['preset_name']}）")
    table.add_row("联盟路由", f"{result['route_decision']}"
                             f"{(' · ' + result['skill']) if result['skill'] else ''}")
    table.add_row("Brief 置信度", str(result["brief_confidence"])
                  + ("（离线规则）" if result["fallback_used"] else ""))
    console.print(table)

    ftable = Table(show_header=True, header_style="bold cyan", title="产物文件")
    ftable.add_column("文件", style="green")
    ftable.add_column("路径", style="dim")
    for name in result["files"]:
        ftable.add_row(name, str(work / name))
    console.print(ftable)
    console.print(f"\n[bold green]✓ 已生成[/bold green]  [cyan]{work / 'output.html'}[/cyan]")


# ============================================================
# 2. feedback
# ============================================================
@main.command()
@click.option("--project", required=True, help="项目目录（expert 的输出目录）")
@click.option("--note", required=True, help="反馈内容（口语化即可）")
@click.option("--dry-run", is_flag=True, help="只解析反馈不重渲染")
def feedback(project: str, note: str, dry_run: bool):
    """反馈迭代：解析反馈 → 改设计 token → 重渲染 output.html。"""
    result = pipeline.run_feedback(project, note, revise=not dry_run)
    if not result.get("ok"):
        if result.get("ask_user"):
            console_err.print(f"[yellow]🦊 {result['ask_user']}[/yellow]")
        else:
            console_err.print(f"[red]✗ {result.get('error', '失败')}[/red]")
        sys.exit(2)
    if result.get("dry_run"):
        console.print(f"[bold green]✓ 反馈解析（dry-run）[/bold green] {result['suggestion']}")
        console.print(f"  规则: [cyan]{', '.join(result['applied_rules']) or '—'}[/cyan]")
        return
    console.print(f"[bold green]✓ 迭代完成[/bold green]  rev{result['revision']}  "
                  f"[cyan]{result['output']}[/cyan]")
    console.print(f"  执行: {result['suggestion']}")
    console.print(f"  规则: [cyan]{', '.join(result['applied_rules']) or '—'}[/cyan]"
                  f"  模型: [dim]{result.get('model', 'rules')}[/dim]")
    console.print(f"  历史: [dim]{Path(result['project']) / 'revisions'}[/dim]")


# ============================================================
# 3. brief
# ============================================================
@main.group()
def brief():
    """Brief 库管理（~/.htmlninefox/briefs/）。"""


@brief.command("list")
def brief_list():
    items = brief_lib.BriefLib().list()
    if not items:
        console.print("[yellow]Brief 库为空[/yellow]  路径: ~/.htmlninefox/briefs/")
        return
    table = Table(title=f"📋 Brief 库 ({len(items)})", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="green")
    table.add_column("Goal", style="white")
    table.add_column("更新时间", style="dim")
    for it in items:
        table.add_row(str(it["id"]), str(it.get("goal", ""))[:60], str(it.get("updated_at", "")))
    console.print(table)


@brief.command("show")
@click.argument("brief_id")
def brief_show(brief_id: str):
    """查看一条 Brief 的完整内容。"""
    path = Path.home() / ".htmlninefox" / "briefs" / f"{brief_id}.json"
    if not path.exists():
        console_err.print(f"[red]✗ 不存在: {path}[/red]")
        sys.exit(2)
    console.print_json(path.read_text(encoding="utf-8"))


@brief.command("add")
@click.option("--from-md", "from_md", required=True, help="从 Markdown 文件添加")
def brief_add(from_md: str):
    src = Path(from_md).expanduser().resolve()
    if not src.exists():
        console_err.print(f"[red]✗ 文件不存在: {src}[/red]")
        sys.exit(2)
    result = brief_lib.BriefLib().add(src)
    console.print(f"[bold green]✓ 已添加 Brief[/bold green]  {result['id']}")


# ============================================================
# 4. template
# ============================================================
@main.command("template")
def template():
    """列出审美模板库（内置 6 风格预设 + 用户模板）。"""
    items = pipeline.list_templates()
    table = Table(title=f"🎨 模板库 ({len(items)})", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="green")
    table.add_column("名称", style="white")
    table.add_column("明暗", style="dim")
    table.add_column("来源", style="dim")
    for it in items:
        table.add_row(it["id"], it["name"], "深色" if it["dark"] else "浅色", it["source"])
    console.print(table)


# ============================================================
# 5. alliance
# ============================================================
@main.group()
def alliance():
    """Skill 联盟管理。"""


@alliance.command("list")
def alliance_list():
    router = AllianceRouter()
    items = router.list_available_skills()
    table = Table(title=f"🤝 Skill 联盟 ({len(items)})", show_header=True, header_style="bold cyan")
    table.add_column("Skill", style="green")
    table.add_column("作者", style="white")
    table.add_column("接管内容", style="cyan")
    table.add_column("状态", style="yellow")
    table.add_column("来源", style="dim")
    for s in items:
        status = "已安装" if s["installed"] else "未安装→本地兜底"
        table.add_row(s["name"], s["author"], ", ".join(s["intents"]) or "—",
                      status, s["source"])
    console.print(table)
    console.print("\n[dim]加入联盟：把 skill-manifest.yaml 放到 ~/.htmlninefox/alliance/[/dim]")


@alliance.command("reload")
def alliance_reload():
    router = AllianceRouter()
    router.reload()
    console.print(f"[bold green]✓ 已重载[/bold green]  {len(router.skills)} 个联盟 skill")


# ============================================================
# 6. app / serve（Web 工作台）
# ============================================================
@main.command("app")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8620, show_default=True, help="首选工作台端口；占用时自动顺延")
@click.option("--output", "-o", default=None, help="生成产物根目录（默认 ~/htmlninefox-output）")
@click.option("--open-browser/--no-open-browser", default=True, show_default=True, help="服务就绪后打开浏览器")
@click.option("--strict-port", is_flag=True, help="端口占用时直接失败，不自动顺延")
def app_command(host: str, port: int, output: str | None, open_browser: bool, strict_port: bool):
    """一键启动工作台；适合 wheel、uv、pipx 与桌面包。"""
    from .launcher import launch_workspace

    launch_workspace(
        host, port, output, open_browser=open_browser,
        fallback_port=not strict_port, distribution="python-app",
    )


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8620, show_default=True, help="工作台端口；占用时自动顺延")
@click.option("--output", "-o", default=None, help="生成产物根目录（默认 ~/htmlninefox-output）")
@click.option("--open-browser/--no-open-browser", default=True, show_default=True)
def workbench(host: str, port: int, output: str | None, open_browser: bool):
    """启动 Web 工作台（v0.4；等价于 app，默认监听 0.0.0.0 便于 Docker/LAN）。"""
    from .launcher import launch_workspace

    launch_workspace(
        host, port, output, open_browser=open_browser,
        fallback_port=True, distribution="workbench",
    )


@main.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8620, show_default=True, help="工作台端口")
@click.option("--output", "-o", default=None, help="生成产物根目录（默认 ~/htmlninefox-output）")
def serve(host: str, port: int, output: str | None):
    """启动 Web 工作台（浏览器端 Brief → 生成 → 预览 → 反馈迭代）。"""
    from .server import app
    app.serve(host, port, output)


# ============================================================
# 兼容旧命令：template-add 占位提示
# ============================================================
@main.command("version")
def version():
    """显示版本信息。"""
    console.print(f"🦊 Html九尾狐 v{__version__} · MIT License")


if __name__ == "__main__":
    main()
