/* Slides lifecycle module: structured editing for deck artifacts.
 * Loads the slide text nodes of a deck project, lets the user edit them,
 * and saves through PUT /slides (expected_revision conflict protection).
 * Every save creates a NEW revision - history is never overwritten. */
(function () {
  'use strict';

  let draft = { projectName: null, nodeId: null, revision: 0, slides: [] };

  async function open(nodeId) {
    const node = nodes.find(item => item.id === nodeId);
    if (!node?.data?.project_name) return flash('该产物缺少项目信息', false);
    draft = { projectName: node.data.project_name, nodeId, revision: 0, slides: [] };
    window.FoxInteraction?.openDialog('#slides-modal', { initialFocus: '.slides-editor' });
    $('#slides-title').textContent = '幻灯片编辑 · ' + node.data.project_name;
    $('#slides-status').textContent = '正在读取幻灯片…';
    $('#slides-editor').innerHTML = '<div class="analysis-empty"><span class="spin">读取分页…</span></div>';
    try {
      const data = await api('/api/projects/' + encodeURIComponent(node.data.project_name) + '/slides');
      draft.revision = data.revision;
      draft.slides = data.slides;
      renderEditor();
      $('#slides-status').textContent = `共 ${data.slides.length} 页 · 修订基于 rev${data.revision}`;
    } catch (error) {
      $('#slides-editor').innerHTML = `<div class="export-warning error">${esc(error.message)}</div>`;
      $('#slides-status').textContent = '读取失败';
    }
  }

  function renderEditor() {
    const editor = document.querySelector('#slides-editor');
    editor.innerHTML = draft.slides.map(slide => {
      const fields = slide.texts.map(text =>
        `<label class="slides-field"><span>文本节点 ${text.node}</span>` +
        `<textarea data-slide="${slide.index}" data-node="${text.node}" rows="2">${esc(text.text)}</textarea></label>`)
        .join('');
      return `<div class="slides-slide"><div class="slides-slide-head">第 ${slide.index + 1} 页</div>${fields}</div>`;
    }).join('');
  }

  async function save() {
    if (draft.busy) return;
    const edits = [];
    document.querySelectorAll('#slides-editor textarea[data-slide]').forEach(area => {
      const original = (draft.slides[Number(area.dataset.slide)]?.texts || [])
        .find(t => t.node === Number(area.dataset.node));
      if (original && area.value !== original.text) {
        edits.push({ slide: Number(area.dataset.slide), node: Number(area.dataset.node),
                     text: area.value });
      }
    });
    if (!edits.length) return flash('没有修改内容', false);
    draft.busy = true;
    window.FoxInteraction?.setBusy('#slides-save', true, '保存中…');
    try {
      const result = await api('/api/projects/' + encodeURIComponent(draft.projectName) +
        '/slides', 'PUT', { edits, expected_revision: draft.revision });
      const node = nodes.find(item => item.id === draft.nodeId);
      if (node) {
        node.data.revision = result.revision;
        const badge = document.querySelector(`#rev-${node.id}`);
        if (badge) badge.textContent = 'rev' + result.revision;
        const preview = document.querySelector(`#frame-${node.id}`);
        if (preview) preview.src = node.data.preview_url + '?t=' + Date.now();
        renderInspector();
      }
      flash(`✓ 幻灯片已更新为 rev${result.revision}，原版本保留`, true);
      close();
    } catch (error) {
      if (error.code === 'revision_conflict') {
        flash('项目已有新版本，请关闭后重新打开编辑', false);
      } else {
        flash('保存失败：' + error.message, false);
      }
    } finally {
      draft.busy = false;
      window.FoxInteraction?.setBusy('#slides-save', false);
    }
  }

  function close() {
    window.FoxInteraction?.closeDialog('#slides-modal');
  }

  window.FoxSlides = { open, close, save };
})();
