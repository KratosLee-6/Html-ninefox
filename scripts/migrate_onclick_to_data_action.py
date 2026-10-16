# -*- coding: utf-8 -*-
"""C6 一次性迁移：全部内联 onclick → data-action 委托。

每条替换都是精确字符串 + 期望次数断言：站点消失、重复出现、或形状漂移
都会硬失败，而不是悄悄漏迁。迁移完成后静态门禁（test_action_registry）
会禁止 onclick 回流。本脚本幂等性不需要——门禁已保证 onclick 归零后
再跑只会硬失败，这正是想要的行为。

  python scripts/migrate_onclick_to_data_action.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

STATIC = Path(__file__).resolve().parents[1] / "htmlninefox" / "server" / "static"

# (文件, 旧串, 新串, 期望次数)。data-* 键与 fox-core.js 的
# FOX_ACTION_SIGNATURES 一一对应。
R: list[tuple[str, str, str, int]] = [
    # ---- index.html：无参动作 ----
    ("index.html", 'onclick="toggleTheme()"', 'data-action="toggleTheme"', 2),
    ("index.html", 'onclick="openAISettings()"', 'data-action="openAISettings"', 2),
    ("index.html", 'onclick="openProjectMemory()"', 'data-action="openProjectMemory"', 2),
    ("index.html", 'onclick="addWorkspace()"', 'data-action="addWorkspace"', 3),
    ("index.html", 'onclick="createDiagnostic()"', 'data-action="createDiagnostic"', 1),
    ("index.html", 'onclick="window.open(\'/classic\',\'_blank\')"', 'data-action="openClassic"', 1),
    ("index.html", 'onclick="openIntake()"', 'data-action="openIntake"', 1),
    ("index.html", 'onclick="openCreatePanel()"', 'data-action="openCreatePanel"', 1),
    ("index.html", 'onclick="advanceActive()"', 'data-action="advanceActive"', 1),
    ("index.html", 'onclick="cancelGeneration()"', 'data-action="cancelGeneration"', 1),
    ("index.html", 'onclick="toggleWorkspaceNavigator()"', 'data-action="toggleWorkspaceNavigator"', 1),
    ("index.html", 'onclick="cycleSnapLevel()"', 'data-action="cycleSnapLevel"', 1),
    ("index.html", 'onclick="fitAll()"', 'data-action="fitAll"', 1),
    ("index.html", 'onclick="closeMobilePanels()"', 'data-action="closeMobilePanels"', 1),
    ("index.html", 'onclick="closeExportCenter()"', 'data-action="closeExportCenter"', 1),
    ("index.html", 'onclick="startExport()"', 'data-action="startExport"', 1),
    ("index.html", 'onclick="closeRevisionDiff()"', 'data-action="closeRevisionDiff"', 1),
    ("index.html", 'onclick="loadRevisionDiff()"', 'data-action="loadRevisionDiff"', 1),
    ("index.html", 'onclick="restoreSelectedRevision()"', 'data-action="restoreSelectedRevision"', 1),
    ("index.html", 'onclick="closeCreatePanel()"', 'data-action="closeCreatePanel"', 1),
    ("index.html", 'onclick="closeAISettings()"', 'data-action="closeAISettings"', 1),
    ("index.html", 'onclick="testAISettings()"', 'data-action="testAISettings"', 1),
    ("index.html", 'onclick="closeSlideEditor()"', 'data-action="closeSlideEditor"', 1),
    ("index.html", 'onclick="saveSlideEditor()"', 'data-action="saveSlideEditor"', 1),
    ("index.html", 'onclick="closeIntake()"', 'data-action="closeIntake"', 1),
    ("index.html", 'onclick="intakeFetch()"', 'data-action="intakeFetch"', 1),
    ("index.html", 'onclick="intakeFetchBatch()"', 'data-action="intakeFetchBatch"', 1),
    ("index.html", 'onclick="openZipPicker()"', 'data-action="openZipPicker"', 1),
    ("index.html", 'onclick="intakeSelectAll()"', 'data-action="intakeSelectAll"', 1),
    ("index.html", 'onclick="closeProjectMemory()"', 'data-action="closeProjectMemory"', 1),
    ("index.html", 'onclick="saveProjectMemory()"', 'data-action="saveProjectMemory"', 1),
    ("index.html", 'onclick="clearProjectMemory()"', 'data-action="clearProjectMemory"', 1),
    ("index.html", 'onclick="sendToCustomWorkspace()"', 'data-action="sendToCustomWorkspace"', 1),
    ("index.html", 'onclick="saveRevisionLabel()"', 'data-action="saveRevisionLabel"', 1),
    ("index.html", 'onclick="analyzeCreation()"', 'data-action="analyzeCreation"', 1),
    ("index.html", 'onclick="saveAISettings()"', 'data-action="saveAISettings"', 1),
    ("workbench-features.js", 'onclick="sendToCustomWorkspace()"',
     'data-action="sendToCustomWorkspace"', 1),
    # ---- index.html：带参动作（键与签名表一致）----
    ("index.html", 'onclick="toggleMobilePanel(\'sidebar\')"',
     'data-action="toggleMobilePanel" data-panel="sidebar"', 1),
    ("index.html", 'onclick="toggleMobilePanel(\'inspector\')"',
     'data-action="toggleMobilePanel" data-panel="inspector"', 1),
    ("index.html", 'onclick="intakeRefresh(\'pending\')"',
     'data-action="intakeRefresh" data-filter="pending"', 1),
    ("index.html", 'onclick="intakeRefresh(\'approved\')"',
     'data-action="intakeRefresh" data-filter="approved"', 1),
    ("index.html", 'onclick="intakeRefresh(\'rejected\')"',
     'data-action="intakeRefresh" data-filter="rejected"', 1),
    ("index.html", 'onclick="intakeRefresh(\'all\')"',
     'data-action="intakeRefresh" data-filter="all"', 1),
    ("index.html", 'onclick="intakeBatch(\'approve\')"',
     'data-action="intakeBatch" data-mode="approve"', 1),
    ("index.html", 'onclick="intakeBatch(\'reject\')"',
     'data-action="intakeBatch" data-mode="reject"', 1),
    # ---- index.html：语义升格（zoomBy 常量 → 语义动作）----
    ("index.html", 'onclick="zoomBy(1.2)"', 'data-action="zoomIn"', 1),
    ("index.html", 'onclick="zoomBy(1/1.2)"', 'data-action="zoomOut"', 1),
    # ---- index.html：productivity 命名空间 → 语义动作 ----
    ("index.html", 'onclick="FoxCanvasProductivity.undo()"', 'data-action="undo"', 1),
    ("index.html", 'onclick="FoxCanvasProductivity.redo()"', 'data-action="redo"', 1),
    ("index.html", 'onclick="FoxCanvasProductivity.toggleSelectionMode()"', 'data-action="toggleSelectionMode"', 1),
    ("index.html", 'onclick="FoxCanvasProductivity.groupSelection()"', 'data-action="groupSelection"', 1),
    ("index.html", 'onclick="FoxCanvasProductivity.toggleLockSelection()"', 'data-action="toggleLockSelection"', 1),
    ("index.html", 'onclick="FoxCanvasProductivity.openSearch()"', 'data-action="openSearch"', 1),
    # ---- index.html：小地图 → canvas-productivity initialize 里 addEventListener ----
    ("index.html", ' onclick="FoxCanvasProductivity.navigateMinimap(event)"', '', 1),
    # ---- fox-core.js：模板字符串（数字节点 id / 工作区 id）----
    ("fox-core.js", 'onclick="event.stopPropagation();fitWs(${n.id})"',
     'data-action="fitWs" data-id="${n.id}"', 1),
    ("fox-core.js", 'onclick="event.stopPropagation();advanceWs(${n.id})"',
     'data-action="advanceWs" data-id="${n.id}"', 1),
    ("fox-core.js", 'onclick="focusWorkspace(${ws.id})"',
     'data-action="focusWorkspace" data-id="${ws.id}"', 1),
    ("fox-core.js", 'onclick="event.stopPropagation();editWorkspace(${ws.id})"',
     'data-action="editWorkspace" data-id="${ws.id}"', 1),
    ("fox-core.js", 'onclick="rerunRecipeStage(${nodeId},\'${stage.id}\')"',
     'data-action="rerunRecipeStage" data-id="${nodeId}" data-stage="${stage.id}"', 1),
    ("fox-core.js", 'onclick="openSlideEditor(${n.id})"',
     'data-action="openSlideEditor" data-id="${n.id}"', 2),
    ("fox-core.js", 'onclick="openRevisionDiff(${n.id})"',
     'data-action="openRevisionDiff" data-id="${n.id}"', 2),
    ("fox-core.js", 'onclick="adoptProject(${n.id})"',
     'data-action="adoptProject" data-id="${n.id}"', 1),
    ("fox-core.js", 'onclick="openOutput(${n.id})"',
     'data-action="openOutput" data-id="${n.id}"', 2),
    ("fox-core.js", 'onclick="openExportCenter(${n.id})"',
     'data-action="openExportCenter" data-id="${n.id}"', 2),
    ("fox-core.js", 'onclick="renameProject(${n.id})"',
     'data-action="renameProject" data-id="${n.id}"', 2),
    ("fox-core.js", 'onclick="duplicateProject(${n.id})"',
     'data-action="duplicateProject" data-id="${n.id}"', 2),
    ("fox-core.js", 'onclick="deleteProject(${n.id})"',
     'data-action="deleteProject" data-id="${n.id}"', 2),
    ("fox-core.js", 'onclick="openCreatePanel(${n.id})"',
     'data-action="openCreatePanel" data-id="${n.id}"', 1),
    ("fox-core.js", 'onclick="advanceWs(${workspaceForNode(n)?.id ?? \'null\'})"',
     'data-action="advanceWs" data-id="${workspaceForNode(n)?.id ?? \'\'}"', 1),
    ("fox-core.js", 'onclick="delNode(${n.id})"',
     'data-action="delNode" data-id="${n.id}"', 3),
    ("fox-core.js", 'onclick="setWorkspaceColor(${n.id},\'${color.hex}\')"',
     'data-action="setWorkspaceColor" data-id="${n.id}" data-color="${color.hex}"', 1),
    ("fox-core.js", 'onclick="fitWs(${n.id})"',
     'data-action="fitWs" data-id="${n.id}"', 1),
    ("fox-core.js", 'onclick="advanceWs(${n.id})"',
     'data-action="advanceWs" data-id="${n.id}"', 1),
    ("fox-core.js", 'onclick="openNodePreview(${n.id})"',
     'data-action="openNodePreview" data-id="${n.id}"', 1),
    # ---- lifecycle-intake.js：字符串候选 id ----
    ("lifecycle-intake.js", 'onclick="intakeApprove(\'${esc(item.candidate_id)}\')"',
     'data-action="intakeApprove" data-id="${esc(item.candidate_id)}"', 1),
    ("lifecycle-intake.js", 'onclick="intakeReject(\'${esc(item.candidate_id)}\')"',
     'data-action="intakeReject" data-id="${esc(item.candidate_id)}"', 1),
    ("lifecycle-intake.js", 'onclick="intakeTogglePreview(\'${esc(item.candidate_id)}\')"',
     'data-action="intakeTogglePreview" data-id="${esc(item.candidate_id)}"', 1),
    ("lifecycle-intake.js", 'onclick="intakeAnalyze(\'${esc(item.candidate_id)}\')"',
     'data-action="intakeAnalyze" data-id="${esc(item.candidate_id)}"', 1),
    ("lifecycle-intake.js", 'onclick="intakeMakeStylePreset(\'${esc(item.candidate_id)}\')"',
     'data-action="intakeMakeStylePreset" data-id="${esc(item.candidate_id)}"', 1),
    ("lifecycle-intake.js", 'onclick="intakeImportComponents(\'${esc(item.candidate_id)}\')"',
     'data-action="intakeImportComponents" data-id="${esc(item.candidate_id)}"', 1),
    ("lifecycle-intake.js", 'onclick="intakeImportMotion(\'${esc(item.candidate_id)}\')"',
     'data-action="intakeImportMotion" data-id="${esc(item.candidate_id)}"', 1),
    # ---- lifecycle-revisions.js：数字修订号 ----
    ("lifecycle-revisions.js", 'onclick="selectRevision(${item.revision})"',
     'data-action="selectRevision" data-revision="${item.revision}"', 1),
    # ---- workbench-features.js ----
    ("workbench-features.js", 'onclick="addGalleryTemplate(\'${item.id}\')"',
     'data-action="addGalleryTemplate" data-id="${item.id}"', 1),
    ("workbench-features.js", 'onclick="previewGalleryPage(\'${item.id}\',\'${page.id}\')"',
     'data-action="previewGalleryPage" data-id="${item.id}" data-page="${page.id}"', 1),
    ("workbench-features.js", 'onclick="removeCreationInput(${index})"',
     'data-action="removeCreationInput" data-index="${index}"', 1),
    ("workbench-features.js", 'onclick="adoptRecommendedAndGenerate()"',
     'data-action="adoptRecommendedAndGenerate"', 1),
    ("workbench-features.js", 'onclick="openGalleryPreview(\'${item.id}\')"',
     'data-action="openGalleryPreview" data-id="${item.id}"', 1),
    # ---- canvas-productivity.js ----
    ("canvas-productivity.js", 'onclick="FoxCanvasProductivity.groupSelection()"',
     'data-action="groupSelection"', 1),
    ("canvas-productivity.js", 'onclick="FoxCanvasProductivity.ungroupSelection()"',
     'data-action="ungroupSelection"', 1),
    ("canvas-productivity.js", 'onclick="FoxCanvasProductivity.toggleLockSelection()"',
     'data-action="toggleLockSelection"', 1),
    ("canvas-productivity.js", 'onclick="FoxCanvasProductivity.deleteSelection()"',
     'data-action="deleteSelection"', 1),
    # ---- classic.html ----
    ("classic.html", 'onclick="loadProjects();return false;"',
     'data-action="loadProjects"', 1),
    ("classic.html", 'onclick="generate()"', 'data-action="generate"', 1),
    ("classic.html", 'onclick="reloadPreview()"', 'data-action="reloadPreview"', 1),
    ("classic.html", 'onclick="sendFeedback()"', 'data-action="sendFeedback"', 1),
    # 项目名过去为嵌进 JS 字符串字面量做了反斜杠转义；data 属性只需要
    # HTML 转义（esc），dataset 解码后拿到的是原始名——更安全也更直。
    ("classic.html",
     'onclick="openProject(\'${p.project.replace(/\\\\/g,\'\\\\\\\\\')}\',\'${p.preview_url}\')"',
     'data-action="openProject" data-project="${esc(p.project)}" data-url="${p.preview_url}"', 1),
]


def main() -> int:
    texts = {name: (STATIC / name).read_text(encoding="utf-8")
             for name in ("index.html", "classic.html", "fox-core.js",
                          "canvas-productivity.js", "lifecycle-intake.js",
                          "lifecycle-revisions.js", "workbench-features.js")}
    errors: list[str] = []
    for name, old, new, expected in R:
        count = texts[name].count(old)
        if count != expected:
            errors.append(f"{name}: {old[:60]!r} 期望 {expected} 处，实际 {count} 处")
            continue
        texts[name] = texts[name].replace(old, new)
    if errors:
        print("HARD FAIL —— 迁移中止，未写任何文件：")
        for e in errors:
            print("  " + e)
        return 1
    for name, text in texts.items():
        (STATIC / name).write_text(text, encoding="utf-8")
    leftover = 0
    for name, text in texts.items():
        n = text.count('onclick="')
        leftover += n
        if n:
            print(f"残留 onclick：{name} × {n}")
    print(f"迁移完成：{len(R)} 组替换全部命中；残留 onclick={leftover}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
