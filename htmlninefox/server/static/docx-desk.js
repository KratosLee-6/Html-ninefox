/**
 * Word 导入审核台（v0.8.1 · step 3）。
 *
 * 只做三件事：把 .docx 换成 base64 交给 /api/intake/docx、把提案摆成可改的
 * 表单、把改过的提案交回 /api/intake/docx/adopt。提案本身是服务器算出来的，
 * 这里不做任何本地推断——界面上看到的理由就是产物用的理由。
 */
(() => {
  const $ = (id) => document.getElementById(id);

  const INTENTS = [
    ['landing', '落地页 landing'],
    ['dashboard', '仪表盘 dashboard'],
    ['deck', '演示 deck'],
    ['poster', '海报 poster'],
    ['archdoc', '架构文档 archdoc'],
    ['doc', '长文档 doc'],
  ];

  const BUILTIN_PRESETS = [
    ['fox-pixel-garden', 'Pixel Garden 像素花园'],
    ['fox-editorial-ink', 'Editorial Ink 编辑部墨'],
    ['fox-swiss-signal', 'Swiss Signal 瑞士信号'],
    ['fox-duotone-studio', 'Duotone Studio 双色工坊'],
    ['fox-soft-silver', 'Soft Silver 柔银'],
    ['doc-clean', 'Doc Clean 文档洁净'],
    ['linear-light', 'Linear Light'],
    ['vercel-dark', 'Vercel Dark'],
    ['shadcn-dashboard', 'shadcn dashboard'],
    ['vibrant-poster', 'Vibrant Poster'],
    ['guizang-magazine', '归藏杂志'],
  ];

  const state = { name: '', base64: '', format: 'docx', proposal: null };

  // 同一张审核台吃两种格式：端点与字段随上传文件的扩展名分流，
  // 服务端两边返回同一份契约（proposal/limitations/counts），渲染不用分叉。
  function formatOf(file) {
    return (file.name || '').toLowerCase().endsWith('.pptx') ? 'pptx' : 'docx';
  }

  function say(text, tone) {
    const el = $('docx-status');
    if (!el) return;
    el.textContent = text || '';
    el.dataset.tone = tone || '';
  }

  function badge(text, kind) {
    const el = $('docx-state');
    if (!el) return;
    el.textContent = text;
    el.dataset.state = kind || 'idle';
  }

  function busy(on, label) {
    const button = $('docx-adopt');
    const analyze = $('docx-analyze');
    if (button) button.disabled = Boolean(on);
    if (analyze) analyze.disabled = Boolean(on);
    if (on && label) badge(label, 'busy');
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error('读取文件失败'));
      reader.onload = () => {
        const text = String(reader.result || '');
        const comma = text.indexOf(',');
        resolve(comma >= 0 ? text.slice(comma + 1) : '');
      };
      reader.readAsDataURL(file);
    });
  }

  function option(select, value, label) {
    const node = document.createElement('option');
    node.value = value;
    node.textContent = label;
    select.append(node);
    return node;
  }

  async function fillPresets(current) {
    const select = $('docx-preset');
    select.replaceChildren();
    const seen = new Set();
    BUILTIN_PRESETS.forEach(([id, label]) => {
      seen.add(id);
      option(select, id, label);
    });
    try {
      const response = await fetch('/api/intake/style-presets');
      const payload = await response.json();
      (payload.presets || []).forEach((preset) => {
        const id = preset.id || preset.name;
        if (!id || seen.has(id)) return;
        seen.add(id);
        option(select, id, `${preset.name || id}（我的模板）`);
      });
    } catch (error) {
      /* 用户模板拉不到不影响内置风格 */
    }
    if (current && !seen.has(current)) option(select, current, current);
    select.value = current || 'fox-pixel-garden';
  }

  function slotRow(item) {
    const row = document.createElement('div');
    row.className = 'docx-slot';
    row.innerHTML = `
      <input data-part="slot" aria-label="位置" maxlength="40">
      <textarea data-part="purpose" aria-label="用途" rows="2" maxlength="60"></textarea>
      <textarea data-part="prompt" aria-label="画面描述" rows="2" maxlength="200"></textarea>
      <button class="btn btn-ghost docx-slot-drop" title="删掉这个图片位">删</button>`;
    row.querySelector('[data-part="slot"]').value = item.slot || '';
    row.querySelector('[data-part="purpose"]').value = item.purpose || '';
    row.querySelector('[data-part="prompt"]').value = item.prompt || '';
    return row;
  }

  function render(payload) {
    const proposal = payload.proposal || {};
    state.proposal = proposal;

    $('docx-headline').value = (proposal.copy && proposal.copy.headline) || '';
    $('docx-summary').value = (proposal.copy && proposal.copy.summary) || '';

    const intent = $('docx-intent');
    intent.replaceChildren();
    INTENTS.forEach(([id, label]) => {
      if (proposal.intent === id || INTENTS.some(([known]) => known === id)) option(intent, id, label);
    });
    if (proposal.intent && !INTENTS.some(([id]) => id === proposal.intent)) {
      option(intent, proposal.intent, proposal.intent);
    }
    intent.value = proposal.intent || 'doc';

    fillPresets((proposal.style && proposal.style.preset_id) || '');
    $('docx-reason').textContent = (proposal.style && proposal.style.reason) || '';

    const slots = $('docx-slots');
    slots.replaceChildren();
    (proposal.image_plan || []).forEach((item) => slots.append(slotRow(item)));

    const limits = $('docx-limits');
    limits.replaceChildren();
    (payload.limitations || []).forEach((line) => {
      const li = document.createElement('li');
      li.textContent = line;
      limits.append(li);
    });
    limits.hidden = !(payload.limitations || []).length;

    $('docx-proposal').hidden = false;
    $('docx-result').hidden = true;
    badge('已出提案', 'ready');
  }

  function collect() {
    const slots = Array.from(document.querySelectorAll('#docx-slots .docx-slot')).map((row) => ({
      slot: row.querySelector('[data-part="slot"]').value.trim(),
      purpose: row.querySelector('[data-part="purpose"]').value.trim(),
      prompt: row.querySelector('[data-part="prompt"]').value.trim(),
    })).filter((item) => item.slot);
    return {
      intent: $('docx-intent').value,
      style: { preset_id: $('docx-preset').value },
      copy: { headline: $('docx-headline').value.trim(), summary: $('docx-summary').value.trim() },
      image_plan: slots,
    };
  }

  async function analyze() {
    const input = $('docx-file');
    const file = input && input.files && input.files[0];
    if (!file) {
      say('先选一份 .docx 或 .pptx 文件。', 'warn');
      return;
    }
    if (file.size > 12 * 1024 * 1024) {
      say('文件超过 12 MB，建议先压缩一下内嵌图片。', 'warn');
      return;
    }
    const format = formatOf(file);
    busy(true, '解析中…');
    say('正在本地解析，不联网。', '');
    try {
      const base64 = await fileToBase64(file);
      const response = await fetch(`/api/intake/${format}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: file.name, [`${format}_base64`]: base64 }),
      });
      const payload = await response.json();
      if (!response.ok) {
        say((payload.error && payload.error.message) || '解析失败，换一份文件试试。', 'error');
        badge('解析失败', 'error');
        return;
      }
      state.name = file.name;
      state.base64 = base64;
      state.format = format;
      render(payload);
      const counts = payload.counts || {};
      const pages = format === 'pptx'
        ? `${counts.heading || 0} 页标题 / ${counts.list || 0} 条要点`
        : `${counts.heading || 0} 个标题 / ${counts.table || 0} 张表`;
      say(`已解析：${pages} / ${counts.image || 0} 张图。改完点「采纳并生成」。`, 'ok');
    } catch (error) {
      say(error.message || '解析失败。', 'error');
      badge('解析失败', 'error');
    } finally {
      busy(false);
    }
  }

  async function adopt() {
    if (!state.base64) {
      say('先解析一份 .docx 或 .pptx。', 'warn');
      return;
    }
    busy(true, '生成中…');
    say('正在生成页面…', '');
    try {
      const format = state.format || 'docx';
      const response = await fetch(`/api/intake/${format}/adopt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: state.name,
          [`${format}_base64`]: state.base64,
          proposal: collect(),
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        say((payload.error && payload.error.message) || '生成失败。', 'error');
        badge('生成失败', 'error');
        return;
      }
      const link = $('docx-result');
      link.href = payload.preview_url;
      link.textContent = `打开产物 ↗ ${payload.project_name}`;
      link.hidden = false;
      badge('已生成', 'done');
      say(`已生成 ${payload.project_name}（${payload.intent} · ${payload.preset_name || payload.preset_id}）。`, 'ok');
      if (window.FoxProjects && typeof window.FoxProjects.load === 'function') window.FoxProjects.load();
    } catch (error) {
      say(error.message || '生成失败。', 'error');
      badge('生成失败', 'error');
    } finally {
      busy(false);
    }
  }

  function addSlot() {
    const slots = $('docx-slots');
    if (!slots) return;
    slots.append(slotRow({ slot: `slot-${slots.children.length + 1}`, purpose: '', prompt: '' }));
  }

  function dropSlot(button) {
    const row = button.closest('.docx-slot');
    if (row) row.remove();
  }

  function reset() {
    state.name = '';
    state.base64 = '';
    state.format = 'docx';
    state.proposal = null;
    const proposal = $('docx-proposal');
    if (proposal) proposal.hidden = true;
    const file = $('docx-file');
    if (file) file.value = '';
    say('');
    badge('待上传', 'idle');
  }

  const picker = $('docx-file');
  if (picker) {
    picker.addEventListener('change', () => {
      const file = picker.files && picker.files[0];
      const name = file && file.name;
      const label = $('docx-filename');
      if (label) label.textContent = name || '选择 .docx / .pptx';
    });
  }

  window.FoxDocx = { analyze, adopt, addSlot, dropSlot, reset, collect };
  document.addEventListener('click', (event) => {
    const drop = event.target.closest('.docx-slot-drop');
    if (drop) dropSlot(drop);
  });
})();
