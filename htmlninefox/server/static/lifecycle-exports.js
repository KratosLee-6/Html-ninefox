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
    // PPTX is only a real capability for deck artifacts; the server rejects
    // anything else, so keep the option hidden instead of offering a failure.
    const pptxOption = document.querySelector('#export-format-pptx');
    if (pptxOption) pptxOption.hidden = manifest.intent !== 'deck';
    // DOCX 只对文字型产物与 deck 讲义有意义；视觉型保持隐藏（选项原因见 PLAN-v0.8）。
    const docxOption = document.querySelector('#export-format-docx');
    if (docxOption) docxOption.hidden = !['doc', 'archdoc', 'deck'].includes(manifest.intent);
    const formatSelect = $('#export-format');
    const recommended = manifest.recommended?.format || 'pdf';
    formatSelect.value = (recommended === 'pptx' && manifest.intent !== 'deck') ? 'pdf' : recommended;
    if (formatSelect.selectedIndex < 0) formatSelect.value = 'pdf';
    $('#export-scope').value = manifest.recommended?.scope || 'auto';
    const runtime = manifest.runtime || {};
    $('#export-runtime').textContent = `本地导出 · ${runtime.engine || 'Chromium'} · ${runtime.package_ready ? '引擎已安装' : '引擎缺失'}。${runtime.install_hint || ''}`;
    syncOptions();
  }

  // 与后端 _export_docx 的 warnings 同源（docx_flattened / docx_external_images /
  // 非语义文本计数）：界面上先讲清楚会丢什么，导完再在结果区逐条确认——
  // 界面 / 报告 / 回读三处口径必须一致（v0.8.2 B3-1）。
  const DEGRADATION = {
    docx: ['CSS 配色、字体、布局不映射，Word 只保留语义结构',
           '外链图片不抓取（离线承诺），只内嵌 data: 图片',
           '非语义容器的文字会计数上报，不强行塞进段落'],
    pptx: ['复杂 CSS 动画与渐变不迁移，PowerPoint 里保留文本与基础形状'],
  };

  function syncOptions() {
    const format = $('#export-format').value;
    const image = format === 'png';
    const fileBridge = format === 'pptx' || format === 'docx';
    $('#export-scale-field').hidden = !image;
    $('#export-paper-field').hidden = image || fileBridge;
    $('#export-landscape-field').hidden = image || fileBridge;
    // Word / PPTX 按页面结构导出，画布尺寸对它们没有意义——以前这两格一直留着，
    // 选了「Word 文档」还让人填 1440×900（v0.8.2 P1）。
    const widthField = $('#export-width-field');
    const heightField = $('#export-height-field');
    if (widthField) widthField.hidden = fileBridge;
    if (heightField) heightField.hidden = fileBridge;
    const pagesField = $('#export-pages')?.closest('.flow-field');
    if (pagesField) pagesField.hidden = fileBridge;

    const degradation = $('#export-degradation');
    if (degradation) {
      const lines = DEGRADATION[format] || [];
      degradation.hidden = !lines.length;
      degradation.innerHTML = lines.length
        ? `<b>这种格式会丢掉什么</b><ul>${lines.map(line => `<li>${esc(line)}</li>`).join('')}</ul>`
        : '';
    }
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
      // The pptx path already returns the report inside `files`; rendering
      // `result.report` again would add a row with an undefined href.
      const entries = [...result.files];
      if (result.report && result.report.download_url) entries.push(result.report);
      const filesHtml = entries.map(file => `<div class="export-file"><span><b>${esc(file.name)}</b><small>${exportBytes(file.bytes)}</small></span><a class="btn btn-secondary" href="${esc(file.download_url)}">下载</a></div>`).join('');
      // 导完把后端 warnings 原样贴出来：界面预告的「会丢什么」与报告、回读
      // 必须是同一套话，否则三处各说一套（B3-1 的验收条件）。
      const warningsHtml = (result.warnings || [])
        .map(item => `<div class="export-warning ${esc(item.level || 'warning')}">${esc(item.message)}</div>`)
        .join('');
      $('#export-result').innerHTML = filesHtml + warningsHtml;
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
