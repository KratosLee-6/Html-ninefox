/* Project lifecycle module: list, rename, duplicate, trash, and canvas sync.
 * Talks to other lifecycle modules only through their window.Fox* APIs and
 * to the shared workbench platform (nodes/edges/state/api/flash/...). */
(function () {
  'use strict';

  async function load() {
    try { state.projects = (await api('/api/projects')).items; } catch (e) { flash('项目列表加载失败：' + e.message, false); }
    if (activeTab === 'files') renderPalette();
  }

  function open(id) {
    const n = nodes.find(x => x.id === id);
    if (n && n.data.preview_url) window.open(n.data.preview_url, '_blank');
  }

  function updateNodes(oldName, project) {
    nodes.filter(n => ['file', 'output'].includes(n.kind) && n.data.project_name === oldName).forEach(n => {
      n.data.project_name = project.name; n.data.project = project.project; n.data.preview_url = project.preview_url;
      n.data.intent = project.intent; n.data.preset_id = project.preset_id; n.data.revision = project.revision;
      n.data.recipe_run = project.recipe_run; n.data.verification = project.verification;
      n.data.memory_applied = project.memory_applied;
      const ws = workspaceForNode(n);
      if (ws) ws.data.recipeRun = project.recipe_run;
      n.data.title = project.name; n.title = project.name;
    });
    nodesEl.innerHTML = ''; nodes.forEach(renderNode); drawEdges(); renderInspector(); save();
  }

  async function rename(id) {
    const n = nodes.find(x => x.id === id); if (!n) return;
    const oldName = n.data.project_name; const newName = prompt('新的项目名称', oldName);
    if (!newName || newName.trim() === oldName) return;
    try {
      const data = await api('/api/projects/' + encodeURIComponent(oldName), 'PATCH', { new_name: newName.trim() });
      updateNodes(oldName, data.project); await load(); flash('项目已重命名为 ' + data.project.name, true);
    } catch (e) { flash('重命名失败：' + e.message, false); }
  }

  async function duplicate(id) {
    const n = nodes.find(x => x.id === id); if (!n) return;
    const suggested = (n.data.project_name || 'project') + '-copy';
    const newName = prompt('副本名称（留空自动命名）', suggested);
    if (newName === null) return;
    try {
      const data = await api('/api/projects/' + encodeURIComponent(n.data.project_name) + '/duplicate', 'POST',
        { new_name: newName.trim() || null });
      const p = data.project; const copy = addNode('file', n.x + 36, n.y + 36, {
        title: p.name, project_name: p.name,
        project: p.project, preview_url: p.preview_url, intent: p.intent, preset_id: p.preset_id, revision: p.revision
      });
      await load(); select(copy.id); flash('已创建副本 ' + p.name, true);
    } catch (e) { flash('复制失败：' + e.message, false); }
  }

  function removeNodes(name) {
    const removed = new Set(nodes.filter(x => ['file', 'output'].includes(x.kind) && x.data.project_name === name).map(x => x.id));
    nodes = nodes.filter(x => !removed.has(x.id));
    edges = edges.filter(e => !removed.has(e.from) && !removed.has(e.to));
    nodesEl.innerHTML = '';
    nodes.forEach(renderNode);
    select(null);
    drawEdges();
    save();
    timeline();
    updateWsCount();
    renderWorkspaceNavigator();
    return removed.size;
  }

  async function trash(id) {
    const n = nodes.find(x => x.id === id); if (!n) return;
    const name = n.data.project_name;
    if (!confirm('将项目“' + name + '”移入回收站？产物不会立即永久删除。')) return;
    try {
      await api('/api/projects/' + encodeURIComponent(name), 'DELETE');
      removeNodes(name);
      await load();
      flash('项目已移入回收站，可从输出目录 .trash 恢复', true);
    } catch (e) {
      if (e.status === 404 || e.code === 'project_not_found') {
        removeNodes(name);
        await load();
        flash('项目文件已不存在，已从画布移除', true);
        return;
      }
      flash('删除失败：' + e.message, false);
    }
  }

  window.FoxProjects = { load, open, rename, duplicate, trash, updateNodes, removeNodes };
})();
