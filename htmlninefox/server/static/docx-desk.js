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

  const state = { name: '', base64: '', format: 'docx', proposal: null, slotLang: 'zh' };

  // 图片位名称的展示层中英切换：服务端契约保持英文 id（cover/section-N），
  // 界面默认中文；用户手改过的名字不属于已知模式，切换时不动它。
  const SLOT_ZH = { cover: '封面主视觉' };
  function slotZhOf(slot) {
    const m = /^(?:section|ch)[-_](\d+)$/.exec((slot || '').trim());
    if (m) return `章节配图 ${m[1]}`;
    return SLOT_ZH[(slot || '').trim()] || null;
  }

  // 同一张审核台吃两种格式：端点与字段随上传文件的扩展名分流，
  // 服务端两边返回同一份契约（proposal/limitations/counts），渲染不用分叉。
  function formatOf(file) {
    const name = (file.name || '').toLowerCase();
    if (name.endsWith('.pptx')) return 'pptx';
    if (name.endsWith('.pdf')) return 'pdf';
    return 'docx';
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
    row.dataset.slot = item.slot || '';
    row.innerHTML = `
      <input data-part="slot" aria-label="图片位位置" maxlength="40" placeholder="位置，如 封面主视觉">
      <textarea data-part="purpose" aria-label="用途" rows="2" maxlength="60" placeholder="这张图用在哪里"></textarea>
      <textarea data-part="prompt" aria-label="画面描述" rows="2" maxlength="200" placeholder="给图像模型的画面描述，可直接改"></textarea>
      <div class="docx-slot-ops">
        <label class="docx-slot-attach" title="挂一张真实图片（可选）">附图<input type="file" accept=".png,.jpg,.jpeg" hidden></label>
        <button class="btn btn-ghost docx-slot-drop" title="删掉这个图片位" aria-label="删除图片位">删</button>
      </div>
      <div class="docx-slot-asset" data-part="asset" hidden></div>`;
    const slotInput = row.querySelector('[data-part="slot"]');
    const zh = slotZhOf(item.slot);
    if (zh) {
      slotInput.dataset.autoZh = zh;
      slotInput.dataset.autoEn = item.slot;
      slotInput.value = state.slotLang === 'zh' ? zh : item.slot;
    } else {
      slotInput.value = item.slot || '';
    }
    row.querySelector('[data-part="purpose"]').value = item.purpose || '';
    row.querySelector('[data-part="prompt"]').value = item.prompt || '';
    if (item.asset && item.asset.width) showAssetChip(row, item.asset);
    const attach = row.querySelector('.docx-slot-attach input');
    attach.addEventListener('change', async () => {
      const file = attach.files && attach.files[0];
      if (!file) return;
      say(`图片位「${slotInput.value || '未命名'}」检查中…`, '');
      try {
        const b64 = await fileToBase64(file);
        const response = await fetch('/api/intake/image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_base64: b64 }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error((payload.error && payload.error.message) || '检查失败');
        const asset = payload.asset;
        row.dataset.imageB64 = b64;
        showAssetChip(row, asset);
        say(`附图检查通过：${asset.format} ${asset.width}×${asset.height}` +
            (asset.dominant_color ? ` · 主色 ${asset.dominant_color}` : ''), 'ok');
      } catch (error) {
        say(error.message || '附图检查失败。', 'error');
      }
    });
    return row;
  }

  function showAssetChip(row, asset) {
    const chip = row.querySelector('[data-part="asset"]');
    chip.hidden = false;
    chip.textContent = `已挂真实图片：${asset.format} ${asset.width}×${asset.height}` +
      (asset.dominant_color ? ` · 主色 ${asset.dominant_color}` : '') +
      ' · 采纳后将进入生成素材';
  }

  function toggleSlotLang() {
    state.slotLang = state.slotLang === 'zh' ? 'en' : 'zh';
    const toggle = $('docx-slot-lang');
    if (toggle) toggle.textContent = state.slotLang === 'zh' ? 'EN' : '中';
    document.querySelectorAll('#docx-slots .docx-slot').forEach((row) => {
      const input = row.querySelector('[data-part="slot"]');
      const zh = input.dataset.autoZh, en = input.dataset.autoEn;
      if (!zh) return;                       // 用户自建位：不存在翻译对
      const current = input.value.trim();
      if (current === zh) input.value = en;   // 仍是自动名才互换
      else if (current === en) input.value = zh;
      // 否则是用户手改过的名字：保留，不动
    });
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
    const slot_images = {};
    document.querySelectorAll('#docx-slots .docx-slot').forEach((row) => {
      const b64 = row.dataset.imageB64;
      if (!b64) return;
      slot_images[row.querySelector('[data-part="slot"]').value.trim()] = b64;
    });
    return {
      intent: $('docx-intent').value,
      style: { preset_id: $('docx-preset').value },
      copy: { headline: $('docx-headline').value.trim(), summary: $('docx-summary').value.trim() },
      image_plan: slots,
      slot_images,
    };
  }

  async function analyze() {
    const input = $('docx-file');
    const file = input && input.files && input.files[0];
    if (!file) {
      say('先选一份 .docx / .pptx / .pdf 文件。', 'warn');
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
        : format === 'pdf'
          ? `${counts.heading || 0} 个标题 / ${counts.paragraph || 0} 段正文`
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
      say('先解析一份文档。', 'warn');
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
      if (label) label.textContent = name || '选择文档';
    });
  }

  window.FoxDocx = { analyze, adopt, addSlot, dropSlot, reset, collect, toggleSlotLang };
  document.addEventListener('click', (event) => {
    const drop = event.target.closest('.docx-slot-drop');
    if (drop) dropSlot(drop);
  });
})();
