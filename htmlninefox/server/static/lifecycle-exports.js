/* Export lifecycle module: export center dialog, preflight analysis, export
 * jobs, downloads, and the privacy-conscious diagnostic bundle. Draft state
 * is private; busy guards keep stale results from overwriting new state. */
(function () {
  'use strict';

  let draft = { nodeId: null, manifest: null };
  let running = null;   /* 提交中的导出 token：旧任务结果不再覆盖新状态 */

  function close() {
    window.FoxInteraction?.closeDialog('#export-modal');
    draft = { nodeId: null, manifest: null };
  }

  async function open(nodeId) {
    const node = nodes.find(item => item.id === nodeId);
    if (!node?.data?.project_name) return flash('该产物缺少项目信息，无法导出', false);
    draft = { nodeId, manifest: null };
    window.FoxInteraction?.openDialog('#export-modal', { initialFocus: '#export-format' });
    $('#export-title').textContent = '导出中心 · ' + node.data.project_name;
    $('#export-analysis').innerHTML = '<div class="analysis-empty"><span class="spin">分析 HTML 结构、分页和动态内容…</span></div>';
    $('#export-status').textContent = '正在分析';
    $('#export-result').innerHTML = '';
    window.FoxInteraction?.setBusy('#export-start', true, '分析中…');
    try {
      const data = await post('/api/exports/analyze', { project_name: node.data.project_name });
      draft.manifest = data.manifest;
      renderAnalysis(data.manifest);
      window.FoxInteraction?.setBusy('#export-start', false);
      $('#export-status').textContent = '分析完成，可以导出';
    } catch (error) {
      window.FoxInteraction?.setBusy('#export-start', false);
      $('#export-start').disabled = true;
      $('#export-analysis').innerHTML = `<div class="export-warning error">${esc(error.message)}</div>`;
      $('#export-status').textContent = '分析失败';
      flash('导出分析失败：' + error.message, false);
    }
  }

  function renderAnalysis(manifest) {
    const paged = manifest.page_model?.paginated;
    const count = manifest.page_model?.count || 1;
    const warnings = manifest.warnings || [];
    $('#export-analysis').innerHTML = `<div class="export-score"><strong>${manifest.compatibility_score}</strong><p><b>${esc(manifest.title)}</b><br>${paged ? `检测到 ${count} 个独立页面，可逐页导出。` : '连续 HTML 页面，默认按长图或自然 PDF 分页导出。'}</p></div>
    <div class="export-meta"><div>内容类型<b>${esc(INTENT_LABEL[manifest.intent] || manifest.intent)}</b></div><div>分页模型<b>${paged ? esc(manifest.page_model.selector) : '连续页面'}</b></div><div>源文件<b>${exportBytes(manifest.source_size)}</b></div><div>动态特性<b>${manifest.features?.length ? esc(manifest.features.join(' / ')) : '静态内容'}</b></div></div>
    <div class="export-warning-list">${warnings.length ? warnings.map(item => `<div class="export-warning ${esc(item.level)}">${esc(item.message)}</div>`).join('') : '<div class="export-warning">未发现阻塞性兼容问题。</div>'}</div>`;
    $('#export-width').value = manifest.viewport?.width || 1440;
    $('#export-height').value = manifest.viewport?.height || 900;
    $('#export-format').value = manifest.recommended?.format || 'pdf';
    $('#export-scope').value = manifest.recommended?.scope || 'auto';
    const runtime = manifest.runtime || {};
    $('#export-runtime').textContent = `本地导出 · ${runtime.engine || 'Chromium'} · ${runtime.package_ready ? '引擎已安装' : '引擎缺失'}。${runtime.install_hint || ''}`;
    syncOptions();
  }

  function syncOptions() {
    const image = $('#export-format').value === 'png';
    $('#export-scale-field').hidden = !image;
    $('#export-paper-field').hidden = image;
    $('#export-landscape-field').hidden = image;
  }

  async function start() {
    const node = nodes.find(item => item.id === draft.nodeId);
    if (!node?.data?.project_name || !draft.manifest) return;
    if (running) return flash('已有导出正在进行，请等待完成', false);
    const token = {};
    running = token;
    const button = $('#export-start');
    button.disabled = true;
    window.FoxInteraction?.setBusy(button, true, '导出中…');
    $('#export-result').innerHTML = '';
    const stale = () => running !== token || draft.nodeId !== node.id;
    try {
      const submitted = await post('/api/exports', {
        project_name: node.data.project_name,
        format: $('#export-format').value,
        scope: $('#export-scope').value,
        pages: $('#export-pages').value,
        width: Number($('#export-width').value),
        height: Number($('#export-height').value),
        scale: Number($('#export-scale').value),
        paper: $('#export-paper').value,
        landscape: $('#export-landscape').checked,
      });
      const result = await window.FoxGeneration.waitForJob(submitted.job.id, job => {
        if (stale()) return;
        $('#export-status').textContent = `任务 ${job.id.slice(0, 8)} · ${job.stage} · ${job.progress}%`;
      }, stale);
      if (stale()) return;   /* 弹窗已切换到其它产物：丢弃旧结果 */
      $('#export-status').textContent = `导出完成 · 兼容性 ${result.compatibility_score} 分 · ${result.browser?.source || 'Chromium'}`;
      $('#export-result').innerHTML = [...result.files, result.report].map(file => `<div class="export-file"><span><b>${esc(file.name)}</b><small>${exportBytes(file.bytes)}</small></span><a class="btn btn-secondary" href="${esc(file.download_url)}">下载</a></div>`).join('');
      flash(`✓ ${node.data.project_name} 已导出 ${result.files.length} 个文件`, true);
    } catch (error) {
      if (stale()) return;
      $('#export-status').textContent = '导出失败：' + error.message;
      $('#export-result').innerHTML = `<div class="export-warning error">${esc(error.message)}<br><small>请确认本机已安装 Edge、Chrome 或 Playwright Chromium。</small></div>`;
    } finally {
      if (running === token) running = null;
      window.FoxInteraction?.setBusy(button, false);
      button.disabled = false;
    }
  }

  async function diagnostic() {
    const button = $('#btn-diagnostic');
    window.FoxInteraction?.setBusy(button, true, '生成中…');
    try {
      flash('正在生成脱敏诊断包…', true, 'info');
      const data = await api('/api/diagnostics', 'POST', {});
      flash('诊断包已生成：' + data.bundle.name, true);
      window.open(data.bundle.download_url, '_blank');
    } catch (e) {
      flash('诊断包生成失败：' + e.message, false);
    } finally {
      window.FoxInteraction?.setBusy(button, false);
    }
  }

  function draftView() { return draft; }

  window.FoxExports = { open, close, renderAnalysis, syncOptions, start, diagnostic, draft: draftView };
})();
