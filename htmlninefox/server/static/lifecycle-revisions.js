/* Revision lifecycle module: history dialog, diff, labels, restore, and the
 * feedback iteration that produces new revisions. Draft state is private;
 * the canvas talks to this module only through its API. */
(function () {
  'use strict';

  let draft = { projectName: null, request: 0, revisions: [], busy: false };

  function close() {
    const nodeId = draft.nodeId;
    draft = { projectName: null, request: draft.request + 1, revisions: [], busy: false };
    window.FoxInteraction?.closeDialog('#revision-modal');
    if (selected === nodeId) requestAnimationFrame(() => $('#btn-revision-diff')?.focus());
  }

  async function open(nodeId) {
    const node = nodes.find(item => item.id === nodeId);
    if (!node?.data?.project_name) return flash('该产物缺少项目信息', false);
    draft = { projectName: node.data.project_name, nodeId, request: draft.request + 1, revisions: [], busy: false };
    $('#revision-title').textContent = '版本差异 · ' + node.data.project_name;
    $('#revision-from').innerHTML = '';
    $('#revision-to').innerHTML = '';
    $('#revision-history').innerHTML = '';
    $('#revision-label').value = '';
    window.FoxInteraction?.openDialog('#revision-modal', { initialFocus: '#revision-close' });
    await load(true);
  }

  async function load(initial = false) {
    const projectName = draft.projectName;
    if (!projectName || draft.busy) return;
    const request = ++draft.request;
    $('#revision-summary').textContent = '正在读取版本…';
    $('#revision-code').textContent = '';
    window.FoxInteraction?.setBusy('#revision-compare', true, '比较中…');
    draft.loading = true;
    updateSelection();
    try {
      const query = initial ? '' : '?from=' + encodeURIComponent($('#revision-from').value) + '&to=' + encodeURIComponent($('#revision-to').value);
      const result = await api('/api/projects/' + encodeURIComponent(projectName) + '/diff' + query);
      if (request !== draft.request) return;   /* 请求序号防竞态：旧响应不覆盖新状态 */
      draft.revisions = result.revisions;
      draft.currentRevision = result.current_revision;
      const options = result.revisions.map(item => `<option value="${item.revision}">rev${item.revision}${item.label ? ' · ' + esc(item.label) : ''}${item.is_current ? ' · 当前' : ''}</option>`).join('');
      $('#revision-from').innerHTML = options;
      $('#revision-to').innerHTML = options;
      $('#revision-from').value = result.from_revision;
      $('#revision-to').value = result.to_revision;
      renderHistory();
      const summary = result.summary;
      $('#revision-summary').textContent = summary.same ? '两个版本内容相同' : `新增 ${summary.added_lines} 行 · 删除 ${summary.removed_lines} 行 · 修改 ${summary.changed_blocks} 处 · ${exportBytes(summary.before_bytes)} → ${exportBytes(summary.after_bytes)}${result.truncated ? ' · 差异过长，已截断' : ''}`;
      $('#revision-code').textContent = result.diff || '无源码变化';
    } catch (error) {
      if (request === draft.request) $('#revision-summary').textContent = '无法比较：' + error.message;
    } finally {
      if (request === draft.request) {
        draft.loading = false;
        window.FoxInteraction?.setBusy('#revision-compare', false);
        updateSelection();
      }
    }
  }

  function renderHistory() {
    const kinds = { generate: '首次生成', feedback: '反馈修改', rerun: '重跑生成', restore: '恢复', checkpoint: '历史检查点', legacy: '早期版本' };
    $('#revision-history').innerHTML = draft.revisions.map(item => `<li><button class="btn btn-secondary" onclick="selectRevision(${item.revision})" ${item.is_current ? 'aria-current="true"' : ''}>rev${item.revision}${item.label ? ' · ' + esc(item.label) : ''}${item.is_current ? ' · 当前' : ''}<small>${kinds[item.kind] || '版本'}${item.parent_revision != null ? ' · 基于 rev' + item.parent_revision : ''}${item.restored_from != null ? ' · 恢复自 rev' + item.restored_from : ''}</small></button></li>`).join('');
  }

  function select(revision) {
    if (draft.busy || draft.loading) return;
    $('#revision-to').value = revision;
    load();
  }

  function updateSelection() {
    const item = draft.revisions.find(item => String(item.revision) === $('#revision-to').value);
    const disabled = Boolean(draft.busy || draft.loading);
    $('#revision-label').value = item?.label || '';
    for (const id of ['revision-from', 'revision-to', 'revision-label', 'revision-save-label']) $("#" + id).disabled = disabled || !item;
    $('#revision-restore').disabled = disabled || !item?.can_restore;
    $('#revision-hint').textContent = item && !item.is_current && !item.can_restore
      ? '这个早期版本没有保存生成配置，可以查看差异和命名，无法完整恢复。'
      : '恢复会保留现有版本，同时恢复所选版本的内容与生成配置。';
  }

  async function mutate(action) {
    const current = draft;
    if (!current.projectName || current.busy || current.loading) return;
    const revision = Number($('#revision-to').value);
    const label = $('#revision-label').value;
    current.busy = true;
    updateSelection();
    window.FoxInteraction?.setBusy('#revision-compare', true);
    try {
      const base = '/api/projects/' + encodeURIComponent(current.projectName);
      if (action === 'label') {
        await api(base + '/revision-label', 'PATCH', { revision, label });
        flash('版本名称已保存', true);
      } else {
        const result = await post(base + '/restore-revision', { revision, expected_revision: current.currentRevision });
        window.FoxProjects?.updateNodes(current.projectName, result.project);
        await persistWorkspaceNow();
        await window.FoxProjects?.load();
        flash(`已从 rev${revision} 恢复为 rev${result.project.revision}，原有版本已保留`, true);
      }
      if (draft === current) {
        current.busy = false;
        await load(action === 'restore');
      }
    } catch (error) {
      if (draft === current) $('#revision-summary').textContent = '操作失败：' + error.message;
      flash('版本操作失败：' + error.message, false);
      if (error.code === 'revision_conflict' && draft === current) {
        current.busy = false;
        await load(true);
      }
    } finally {
      current.busy = false;
      if (draft === current) {
        window.FoxInteraction?.setBusy('#revision-compare', false);
        updateSelection();
      }
    }
  }

  function saveLabel() { return mutate('label'); }
  function restore() { return mutate('restore'); }

  async function sendFeedback(n) {
    const note = document.querySelector('#fb-note').value.trim();
    if (!note) return;
    const btn = document.querySelector('#fb-send'); btn.disabled = true;
    try {
      const d = await post('/api/feedback', { project: n.data.project, note });
      n.data.revision = d.revision;
      n.data.feedback = n.data.feedback || [];
      n.data.feedback.unshift({ rev: d.revision, note, sug: d.suggestion || '' });
      document.querySelector(`#rev-${n.id}`).textContent = 'rev' + d.revision;
      document.querySelector(`#frame-${n.id}`).src = n.data.preview_url + '?t=' + Date.now();
      renderInspector(); flash(`✓ rev${d.revision}：${d.suggestion || '已迭代'}`, true); window.FoxProjects?.load();
    } catch (e) { flash('🦊 ' + e.message, false); }
    finally { btn.disabled = false; }
  }

  window.FoxRevisions = { open, close, load, select, updateSelection, saveLabel, restore, sendFeedback };
})();
