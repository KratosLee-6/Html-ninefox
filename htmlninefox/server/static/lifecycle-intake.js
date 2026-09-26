/* Intake lifecycle module: design reference review workbench.
 * Fetches public reference pages into pending candidates (server-side
 * safety gate), lists them, and approves/rejects each one. Approved
 * candidates become private-template gallery items via /approve. */
(function () {
  'use strict';

  let filter = 'pending';
  let sourceFilter = '';
  const selected = new Set();

  async function open() {
    window.FoxInteraction?.openDialog('#intake-modal', { initialFocus: '#intake-fetch-url' });
    await loadSources();
    await refresh();
  }

  function close() {
    window.FoxInteraction?.closeDialog('#intake-modal');
  }

  async function loadSources() {
    const select = document.querySelector('#intake-source');
    if (!select) return;
    try {
      const data = await api('/api/intake/sources');
      window.__intakeSources = data.sources || [];
      select.innerHTML = '<option value="">（不指定来源）</option>' + window.__intakeSources.map(
        source => `<option value="${esc(source.id)}">${esc(source.name)} · ${
          { open: '开放', reference: '参考', 'inspiration-only': '灵感' }[source.license_class] || source.license_class}</option>`).join('');
    } catch (error) { /* 源清单加载失败不阻塞审核 */ }
  }

  async function refresh(nextFilter, nextSource) {
    if (nextFilter) filter = nextFilter;
    if (nextSource !== undefined) sourceFilter = nextSource;
    selected.clear();
    const list = document.querySelector('#intake-list');
    if (!list) return;
    list.innerHTML = '<div class="analysis-empty"><span class="spin">读取候选素材…</span></div>';
    try {
      const query = new URLSearchParams({ status: filter });
      if (sourceFilter) query.set('source', sourceFilter);
      const data = await api('/api/intake/candidates?' + query.toString());
      renderList(data.candidates || []);
      renderSourceFilter(data.sources || []);
    } catch (error) {
      list.innerHTML = `<div class="export-warning error">${esc(error.message)}</div>`;
    }
  }

  function renderSourceFilter(sources) {
    const select = document.querySelector('#intake-source-filter');
    if (!select) return;
    const current = sourceFilter;
    select.innerHTML = '<option value="">全部来源</option>' + sources.map(
      source => `<option value="${esc(source.id)}">${esc(source.name)}</option>`).join('');
    select.value = current;
  }

  function renderList(candidates) {
    const list = document.querySelector('#intake-list');
    if (!candidates.length) {
      list.innerHTML = '<p class="ins-empty">暂无候选素材。粘贴一个公开网页地址，点「抓取为候选」。</p>';
      return;
    }
    const sourceNames = {};
    (window.__intakeSources || []).forEach(source => { sourceNames[source.id] = source.name; });
    list.innerHTML = candidates.map(item => {
      const licenseLabel = { open: '开放许可', reference: '仅参考重写', 'inspiration-only': '仅灵感板' }[item.license_class] || item.license_class;
      const colors = (item.tokens?.colors || []).slice(0, 6).map(color =>
        `<span class="intake-swatch" style="background:${esc(color)}" title="${esc(color)}"></span>`).join('');
      const headings = (item.skeleton?.headings || []).slice(0, 4).map(h => esc(h.text)).join(' · ');
      return `<div class="intake-card">
        <div class="intake-card-head">
          ${item.status === 'pending' ? `<input type="checkbox" class="intake-check" data-id="${esc(item.candidate_id)}" style="width:auto;height:auto" aria-label="选中 ${esc(item.title)}">` : ''}
          <b>${esc(item.title)}</b>
          <span class="intake-badge">${esc(licenseLabel)}</span>
          ${item.source ? `<span class="intake-badge dim">${esc(sourceNames[item.source] || item.source)}</span>` : ''}
          <span class="intake-badge dim">${esc(item.intent_guess)}</span></div>
        <div class="intake-card-url">${esc(item.final_url)}</div>
        ${colors ? `<div class="intake-swatches">${colors}</div>` : ''}
        ${headings ? `<div class="intake-outline">${headings}</div>` : ''}
        <div class="intake-card-actions">
          ${item.status === 'pending'
            ? `<button class="btn btn-primary" onclick="intakeApprove('${esc(item.candidate_id)}')">✔ 采纳为模板</button>
               <button class="btn btn-danger-ghost" onclick="intakeReject('${esc(item.candidate_id)}')">✕ 拒绝</button>
               <button class="btn btn-secondary" onclick="intakeTogglePreview('${esc(item.candidate_id)}')">👁 预览</button>`
            : `${item.status === 'approved'
                ? `<button class="btn btn-secondary" onclick="intakeMakeStylePreset('${esc(item.candidate_id)}')">🎨 生成风格预设</button>`
                : `<span class="intake-status">已拒绝</span>`}`}
        </div>
        <iframe class="intake-preview" id="intake-preview-${esc(item.candidate_id)}" hidden
          sandbox title="${esc(item.title)} 预览"
          src="/api/intake/candidates/${esc(item.candidate_id)}/preview"></iframe>
      </div>`;
    }).join('');
  }

  async function fetchCandidate() {
    const input = document.querySelector('#intake-fetch-url');
    const status = document.querySelector('#intake-status');
    const url = (input.value || '').trim();
    if (!url) return flash('请先粘贴要参考的网页地址', false);
    const sourceId = document.querySelector('#intake-source')?.value || '';
    window.FoxInteraction?.setBusy('#intake-fetch-btn', true, '抓取中…');
    status.textContent = '正在安全抓取并解析页面…';
    try {
      const result = await post('/api/intake/fetch', { url, source_id: sourceId || null });
      input.value = '';
      status.textContent = '已生成候选：' + result.candidate.title;
      flash('✓ 候选素材已生成，等待审核', true);
      await refresh(filter === 'all' ? 'all' : 'pending');
    } catch (error) {
      status.textContent = '抓取失败：' + error.message;
      flash('抓取失败：' + error.message, false);
    } finally {
      window.FoxInteraction?.setBusy('#intake-fetch-btn', false);
    }
  }

  async function fetchBatch() {
    const box = document.querySelector('#intake-batch-urls');
    const status = document.querySelector('#intake-status');
    const urls = (box.value || '').split('\n').map(line => line.trim()).filter(Boolean);
    if (!urls.length) return flash('请先在文本框中粘贴 URL（每行一个）', false);
    const sourceId = document.querySelector('#intake-source')?.value || '';
    window.FoxInteraction?.setBusy('#intake-batch-btn', true, '批量抓取中…');
    status.textContent = `正在批量抓取 ${urls.length} 个地址（每来源限速，请稍候）…`;
    try {
      const result = await post('/api/intake/fetch-batch', { urls, source_id: sourceId || null });
      box.value = '';
      const okCount = (result.created || []).length;
      const failCount = (result.failed || []).length;
      status.textContent = `批量完成：成功 ${okCount} 个，失败 ${failCount} 个` +
        (failCount ? '（失败项多为私网地址或不可达）' : '');
      flash(`✓ 批量抓取完成：成功 ${okCount}，失败 ${failCount}`, failCount === 0);
      await refresh(filter === 'all' ? 'all' : 'pending');
    } catch (error) {
      status.textContent = '批量抓取失败：' + error.message;
      flash('批量抓取失败：' + error.message, false);
    } finally {
      window.FoxInteraction?.setBusy('#intake-batch-btn', false);
    }
  }

  async function importZip(file) {
    const status = document.querySelector('#intake-status');
    if (!file) return;
    window.FoxInteraction?.setBusy('#intake-zip-btn', true, '导入中…');
    status.textContent = `正在解析 ${file.name}…`;
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const zipBase64 = String(reader.result).split(',')[1] || '';
        const result = await post('/api/intake/zip', {
          zip_base64: zipBase64, name: file.name.replace(/\.zip$/i, ''),
        });
        const count = (result.created || []).length;
        status.textContent = `ZIP 导入完成：${count} 个候选等待审核`;
        flash(`✓ ZIP 导入 ${count} 个候选`, true);
        await refresh(filter === 'all' ? 'all' : 'pending');
      } catch (error) {
        status.textContent = 'ZIP 导入失败：' + error.message;
        flash('ZIP 导入失败：' + error.message, false);
      } finally {
        window.FoxInteraction?.setBusy('#intake-zip-btn', false);
      }
    };
    reader.readAsDataURL(file);
  }

  async function approve(candidateId) {
    try {
      const result = await post('/api/intake/candidates/' + encodeURIComponent(candidateId) + '/approve', {});
      flash('✓ 已采纳为私人模板：' + (result.gallery_item?.name || candidateId), true);
      await loadGallery();
      await refresh(filter);
    } catch (error) {
      flash('采纳失败：' + error.message, false);
    }
  }

  async function reject(candidateId) {
    try {
      await post('/api/intake/candidates/' + encodeURIComponent(candidateId) + '/reject', {});
      await refresh(filter);
    } catch (error) {
      flash('拒绝失败：' + error.message, false);
    }
  }

  function togglePreview(candidateId) {
    const frame = document.getElementById('intake-preview-' + candidateId);
    if (frame) frame.hidden = !frame.hidden;
  }

  function toggleSelect(candidateId, checked) {
    if (checked) selected.add(candidateId);
    else selected.delete(candidateId);
    const bar = document.querySelector('#intake-batch-bar');
    if (bar) {
      bar.hidden = selected.size === 0;
      const label = document.querySelector('#intake-batch-count');
      if (label) label.textContent = `已选 ${selected.size} 项`;
    }
  }

  function selectAllPending() {
    document.querySelectorAll('.intake-check').forEach(box => {
      box.checked = true;
      selected.add(box.dataset.id);
    });
    const bar = document.querySelector('#intake-batch-bar');
    if (bar) {
      bar.hidden = selected.size === 0;
      const label = document.querySelector('#intake-batch-count');
      if (label) label.textContent = `已选 ${selected.size} 项`;
    }
  }

  async function batchApply(action) {
    if (!selected.size) return;
    const ids = [...selected];
    try {
      const result = await post('/api/intake/candidates/batch', { action, ids });
      const okCount = (result.results || []).filter(item => item.ok).length;
      flash(`✓ 批量${action === 'approve' ? '采纳' : '拒绝'}完成：${okCount}/${ids.length}`, okCount === ids.length);
      if (action === 'approve') await loadGallery();
      await refresh(filter);
    } catch (error) {
      flash('批量操作失败：' + error.message, false);
    }
  }

  async function makeStylePreset(candidateId) {
    try {
      const result = await post('/api/intake/style-presets/create', { candidate_id: candidateId });
      flash('✓ 风格预设已生成：' + result.preset.name + '（可在风格面板应用）', true);
      await refresh(filter);
    } catch (error) {
      flash('风格预设生成失败：' + error.message, false);
    }
  }

  window.FoxIntake = {
    open, close, refresh, fetchCandidate, fetchBatch, importZip,
    approve, reject, togglePreview, toggleSelect, selectAllPending, batchApply, makeStylePreset,
  };
})();
