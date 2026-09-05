/* Html九尾狐 workbench feature layer: gallery, multimodal input, and AI settings. */
let creationDraft = { inputs: [], analysis: null, requirementId: null };

function galleryItem(id) {
  return state.gallery.find(item => item.id === id);
}

async function loadGallery() {
  try {
    state.gallery = (await api('/api/gallery')).items || [];
  } catch (error) {
    state.gallery = [];
    flash('模板作品库加载失败：' + error.message, false);
  }
  if (['layouts', 'blocks', 'styles'].includes(activeTab)) renderPalette();
}

function updateTemplateImportVisibility() {
  const bar = document.querySelector('#template-import-bar');
  if (bar) bar.hidden = activeTab !== 'layouts';
}

function fileAsBase64(file) {
  return file.arrayBuffer().then(buffer => {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let offset = 0; offset < bytes.length; offset += 32768) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
    }
    return btoa(binary);
  });
}

async function importTemplateFiles(fileList, folderMode = false) {
  const files = [...fileList];
  if (!files.length) return;
  const rootName = folderMode ? (files[0].webkitRelativePath || '').split('/')[0] : '';
  const fallbackName = rootName || files[0].name.replace(/\.html?$/i, '');
  const name = prompt('私人模板名称', fallbackName);
  if (name === null) return;
  const buttons = ['#import-html-button', '#import-folder-button'].map(selector => $(selector));
  buttons.forEach(button => { if (button) button.disabled = true; });
  flash(`正在导入 ${files.length} 个文件…`, true);
  try {
    const payloadFiles = [];
    for (const file of files) {
      let relativePath = file.webkitRelativePath || file.name;
      if (folderMode && rootName && relativePath.startsWith(rootName + '/')) {
        relativePath = relativePath.slice(rootName.length + 1);
      }
      payloadFiles.push({ path:relativePath, data_base64:await fileAsBase64(file) });
    }
    const entryItem = payloadFiles.find(item => /(^|\/)index\.html?$/i.test(item.path))
      || payloadFiles.find(item => /\.html?$/i.test(item.path));
    const result = await api('/api/gallery/import', 'POST', {
      name:name.trim(), entry:entryItem?.path || '', files:payloadFiles,
    });
    await loadGallery();
    activeTab = 'layouts';
    document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('on', tab.dataset.tab === 'layouts'));
    updateTemplateImportVisibility();
    renderPalette();
    flash(`已导入私人模板：${result.item.name} · ${result.item.pages.length} 个页面`, true);
  } catch (error) {
    flash('模板导入失败：' + error.message, false);
  } finally {
    buttons.forEach(button => { if (button) button.disabled = false; });
    $('#import-html-input').value = '';
    $('#import-folder-input').value = '';
  }
}

async function deleteUserGallery(itemId) {
  const item = galleryItem(itemId);
  if (!item || item.source !== 'user') return;
  if (!confirm(`删除私人模板“${item.name}”？本地模板包会被移除。`)) return;
  try {
    await api('/api/gallery/' + encodeURIComponent(itemId), 'DELETE');
    await loadGallery();
    renderPalette();
    flash('已删除私人模板：' + item.name, true);
  } catch (error) {
    flash('删除模板失败：' + error.message, false);
  }
}

$('#import-html-button').addEventListener('click', () => $('#import-html-input').click());
$('#import-folder-button').addEventListener('click', () => $('#import-folder-input').click());
$('#import-html-input').addEventListener('change', event => importTemplateFiles(event.target.files, false));
$('#import-folder-input').addEventListener('change', event => importTemplateFiles(event.target.files, true));
updateTemplateImportVisibility();

function galleryTemplateData(item) {
  return {
    title: item.name,
    intent: item.intent,
    template: item.preset_id,
    preset: item.preset_id,
    gallery_id: item.id,
    preview_url: item.preview_url,
    pages: item.pages,
    origin: item.origin,
    description: item.description,
  };
}

function galleryPageData(item, page) {
  return {
    title: page.name,
    blockId: page.block_id,
    page_id: page.id,
    gallery_id: item.id,
    template: item.preset_id,
    intent: item.intent,
    preview_url: page.preview_url,
    origin: item.origin,
    text: page.headline,
  };
}

PALETTE.layouts = () => {
  const privateItems = state.gallery.filter(item => item.source === 'user');
  const builtInItems = state.gallery.filter(item => item.source !== 'user');
  const cards = items => items.map(item => ({
      id:'gallery-layout-' + item.id,
      t:item.name,
      name:item.name,
      en:item.description,
      galleryCard:true,
      galleryId:item.id,
      previewUrl:item.preview_url,
      previewIntent:item.intent,
      previewTemplate:item.preset_id,
      userGallery:item.source === 'user',
      drag:{ kind:'template', data:galleryTemplateData(item) },
    }));
  if (!state.gallery.length) return [{ header:'真实模板作品加载中…' }];
  return [
    { group:'私人模板 · 用得越多，推荐越靠前' },
    ...(privateItems.length ? cards(privateItems) : [{ header:'可导入单个 HTML，或包含资源的完整文件夹。私人模板只保存在本地。' }]),
    { group:'内置真实 HTML 模板 · 放大查看全部页面' },
    ...cards(builtInItems),
  ];
};

PALETTE.blocks = () => {
  const pages = state.gallery.flatMap(item => item.pages.map(page => ({
    id:'gallery-page-' + item.id + '-' + page.id,
    t:page.name,
    name:page.name,
    en:item.name + ' · ' + page.headline,
    galleryCard:true,
    galleryId:item.id,
    galleryPageId:page.id,
    previewUrl:page.preview_url,
    previewIntent:item.intent,
    previewTemplate:item.preset_id,
    drag:{ kind:'block', data:galleryPageData(item, page) },
  })));
  const primitives = BLOCKS.map(block => ({
    id:'primitive-' + block.id,
    t:block.t,
    name:block.t,
    mini:miniOf('block', block.id),
    drag:{ kind:'block', data:{ title:block.t, blockId:block.id } },
  }));
  return [{ group:'可抽取的真实页面 · 单页加入工作区' }, ...pages,
          { group:'基础内容区块 · 快速补充' }, ...primitives];
};

const originalStylesPalette = PALETTE.styles;
PALETTE.styles = () => {
  const showcases = state.gallery.map(item => ({
    id:'gallery-style-' + item.id,
    t:item.name,
    name:item.name,
    en:item.origin,
    galleryCard:true,
    galleryId:item.id,
    previewUrl:item.preview_url,
    previewIntent:item.intent,
    previewTemplate:item.preset_id,
    drag:{ kind:'style', data:{
      title:item.name,
      intent:item.intent,
      preset:item.preset_id,
      gallery_id:item.id,
      preview_url:item.preview_url,
      origin:item.origin,
    } },
  }));
  return [{ group:'真实风格作品 · 看完整页面节奏' }, ...showcases,
          { group:'设计 Token 与色彩预设' }, ...originalStylesPalette().filter(item => !item.group)];
};

function activeOrCreateWorkspace() {
  return activeWorkspace() || addWorkspace();
}

function addMaterialToWorkspace(kind, data, index = 0) {
  const ws = activeOrCreateWorkspace();
  const columns = Math.max(1, Math.floor((ws.w - 90) / 250));
  const x = ws.x + 38 + (index % columns) * 248;
  const y = ws.y + 72 + Math.floor(index / columns) * 178;
  const node = addNode(kind, x, y, { ...JSON.parse(JSON.stringify(data)), workspaceId: ws.id });
  node.workspaceId = ws.id;
  save();
  return node;
}

function addGalleryTemplate(itemId) {
  const item = galleryItem(itemId);
  if (!item) return;
  const ws = activeOrCreateWorkspace();
  const existing = membersOf(ws).find(node => node.kind === 'template' && node.data.gallery_id === item.id);
  const node = existing || addMaterialToWorkspace('template', galleryTemplateData(item), membersOf(ws).length);
  select(node.id);
  flash('已加入整套模板：' + item.name, true);
}

function addGalleryPage(itemId, pageId) {
  const item = galleryItem(itemId);
  const page = item?.pages.find(entry => entry.id === pageId);
  if (!item || !page) return;
  const ws = activeOrCreateWorkspace();
  const existing = membersOf(ws).find(node => node.kind === 'block' && node.data.gallery_id === item.id && node.data.page_id === page.id);
  const node = existing || addMaterialToWorkspace('block', galleryPageData(item, page), membersOf(ws).length);
  select(node.id);
  flash('已抽取页面：' + page.name, true);
}

function previewGalleryPage(itemId, pageId = '') {
  const item = galleryItem(itemId);
  if (!item) return;
  const page = item.pages.find(entry => entry.id === pageId);
  const url = page?.preview_url || item.preview_url;
  $('#preview-frame').src = url;
  $('#preview-open-window').onclick = () => window.open(url, '_blank');
  const extract = $('#preview-extract-page');
  if (extract) {
    extract.hidden = !page;
    extract.textContent = page ? '抽取页面：' + page.name : '抽取当前页面';
    extract.onclick = page ? () => addGalleryPage(item.id, page.id) : null;
  }
  document.querySelectorAll('.preview-page').forEach(button => button.classList.toggle('on', button.dataset.pageId === pageId));
}

function openGalleryPreview(itemId, pageId = '') {
  const item = galleryItem(itemId);
  if (!item) return;
  $('#preview-title').textContent = item.name;
  $('#preview-meta').textContent = `${INTENT_LABEL[item.intent]} · ${item.pages.length} 个页面 · ${item.preset_id}`;
  $('#preview-pages').hidden = false;
  $('#preview-pages').innerHTML = `<div class="preview-actions">
    <button class="btn btn-primary" onclick="addGalleryTemplate('${item.id}')">整套加入工作区</button>
    <button class="btn btn-secondary" id="preview-extract-page" hidden>抽取当前页面</button>
  </div><p class="gallery-origin">${esc(item.description)}<br>${esc(item.origin)}</p>
  <div class="preview-page-list">${item.pages.map((page, index) => `<button class="preview-page ${page.id===pageId?'on':''}" data-page-id="${page.id}" onclick="previewGalleryPage('${item.id}','${page.id}')" ondblclick="addGalleryPage('${item.id}','${page.id}')"><b>${String(index+1).padStart(2,'0')}</b><span><strong>${esc(page.name)}</strong><br>${esc(page.headline)}</span></button>`).join('')}</div>`;
  previewGalleryPage(item.id, pageId);
  $('#preview-modal').hidden = false;
}

function openNodePreview(id) {
  const node = nodes.find(item => item.id === id);
  if (!node) return;
  if (node.data.gallery_id) return openGalleryPreview(node.data.gallery_id, node.data.page_id || '');
  openTemplatePreview(node.data.intent || 'landing', node.data.template || node.data.preset || '', node.data.title || node.title);
}

async function loadAISettings() {
  try {
    state.ai = (await api('/api/settings/ai')).settings;
  } catch (error) {
    state.ai = { enabled:false, api_key_set:false };
  }
  const button = $('#btn-ai-settings');
  button?.classList.toggle('ai-ready', Boolean(state.ai.enabled));
  if ($('#ai-status-glyph')) $('#ai-status-glyph').textContent = state.ai.enabled ? '●' : '◇';
}

async function openAISettings() {
  await loadAISettings();
  $('#ai-enabled').checked = Boolean(state.ai.enabled);
  $('#ai-provider').value = state.ai.provider || 'openai-compatible';
  $('#ai-model').value = state.ai.model || '';
  $('#ai-base-url').value = state.ai.base_url || '';
  $('#ai-api-key').value = '';
  $('#ai-clear-key').checked = false;
  $('#ai-api-key').placeholder = state.ai.api_key_set ? '已保存；留空不修改' : '输入 API Key；本地保存';
  $('#ai-settings-status').textContent = state.ai.enabled
    ? `AI 已启用 · ${state.ai.model || '未填写模型'} · Key ${state.ai.api_key_set ? '已设置' : '未设置'}`
    : '当前使用离线规则引擎；无需 API Key 也可以生成。';
  $('#ai-modal').hidden = false;
}

function closeAISettings() {
  $('#ai-modal').hidden = true;
  $('#ai-api-key').value = '';
}

async function saveAISettings() {
  const status = $('#ai-settings-status');
  status.textContent = '正在保存…';
  try {
    const result = await api('/api/settings/ai', 'PUT', {
      enabled: $('#ai-enabled').checked,
      provider: $('#ai-provider').value,
      model: $('#ai-model').value.trim(),
      base_url: $('#ai-base-url').value.trim().replace(/\/$/, ''),
      api_key: $('#ai-api-key').value.trim(),
      clear_api_key: $('#ai-clear-key').checked,
    });
    state.ai = result.settings;
    await loadAISettings();
    status.textContent = `保存成功 · ${state.ai.enabled ? 'AI 已启用' : '离线规则模式'} · Key ${state.ai.api_key_set ? '已设置' : '未设置'}`;
  } catch (error) {
    status.textContent = '保存失败：' + error.message;
  }
}

async function testAISettings() {
  const status = $('#ai-settings-status');
  status.textContent = '正在测试模型连接…';
  try {
    await saveAISettings();
    const result = await api('/api/settings/ai/test', 'POST', {});
    status.textContent = `连接成功 · ${result.model} · ${result.reply || 'OK'}`;
  } catch (error) {
    status.textContent = '连接失败：' + error.message;
  }
}

function openCreatePanel(requirementId = null) {
  creationDraft.requirementId = requirementId;
  creationDraft.analysis = null;
  const requirement = nodes.find(node => node.id === requirementId && node.kind === 'requirement');
  creationDraft.inputs = JSON.parse(JSON.stringify(requirement?.data.attachments || []));
  $('#creation-prompt').value = requirement?.data.text || '';
  $('#creation-analysis').className = 'analysis-empty';
  $('#creation-analysis').innerHTML = '输入需求后，系统会推荐内容类型、真实 HTML 模板、页面组合和视觉风格。你可以直接采用，也可以进入工作区自行调整版式、内容、风格、文件和技能。';
  renderCreationInputs();
  $('#create-modal').hidden = false;
  setTimeout(() => $('#creation-prompt').focus(), 30);
}

function closeCreatePanel() {
  $('#create-modal').hidden = true;
}

function renderCreationInputs() {
  $('#creation-input-list').innerHTML = creationDraft.inputs.map((item, index) => `<div class="input-item"><span>${esc(item.name)}<br><small>${esc(item.kind)} · ${Math.ceil((item.size || 0)/1024)}KB</small></span><button onclick="removeCreationInput(${index})">×</button></div>`).join('');
}

function removeCreationInput(index) {
  creationDraft.inputs.splice(index, 1);
  renderCreationInputs();
}

function bytesToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  const chunk = 0x8000;
  for (let index = 0; index < bytes.length; index += chunk) {
    binary += String.fromCharCode(...bytes.subarray(index, Math.min(index + chunk, bytes.length)));
  }
  return btoa(binary);
}

async function uploadCreationFiles(files) {
  const button = $('#creation-analyze');
  for (const file of files) {
    if (file.size > 8 * 1024 * 1024) {
      flash(file.name + ' 超过 8MB，已跳过', false);
      continue;
    }
    button.disabled = true;
    button.textContent = '上传 ' + file.name;
    try {
      const result = await api('/api/inputs', 'POST', {
        name:file.name,
        mime:file.type || 'application/octet-stream',
        data_base64:bytesToBase64(await file.arrayBuffer()),
      });
      creationDraft.inputs.push(result.input);
      renderCreationInputs();
    } catch (error) {
      flash('附件上传失败：' + error.message, false);
    }
  }
  button.disabled = false;
  button.textContent = 'AI 分析并推荐';
  $('#creation-files').value = '';
}

$('#creation-files').addEventListener('change', event => uploadCreationFiles([...event.target.files]));

async function analyzeCreation() {
  const prompt = $('#creation-prompt').value.trim();
  if (!prompt && !creationDraft.inputs.length) return flash('请填写文字需求或添加附件', false);
  const button = $('#creation-analyze');
  button.disabled = true;
  button.textContent = '分析中…';
  $('#creation-analysis').className = 'analysis-empty';
  $('#creation-analysis').textContent = 'AI 正在拆解需求并匹配真实模板…';
  try {
    const analysis = await post('/api/analyze', { prompt, inputs:creationDraft.inputs.map(item => item.id) });
    creationDraft.analysis = analysis;
    const item = analysis.recommended_template;
    $('#creation-analysis').className = '';
    $('#creation-analysis').innerHTML = `<div class="analysis-chips"><span>${esc(INTENT_LABEL[analysis.intent])}</span><span>${esc(analysis.preset_id)}</span><span>${analysis.engine === 'llm' ? 'AI 模型' : '离线规则'}</span><span>置信度 ${Math.round((analysis.confidence || 0)*100)}%</span></div>
      <div class="recommend-title">${esc(item.name)}</div><div class="recommend-desc">${esc(item.description)}</div>
      <div class="recommend-preview"><iframe src="${esc(item.preview_url)}" sandbox="allow-scripts allow-same-origin"></iframe></div>
      <div class="analysis-chips">${item.pages.map(page => `<span>${esc(page.name)}</span>`).join('')}</div>
      <div class="flow-actions"><button class="btn btn-primary" onclick="adoptRecommendedAndGenerate()">采用推荐并生成</button><button class="btn btn-secondary" onclick="sendToCustomWorkspace()">进入工作区自定义</button><button class="btn btn-ghost" onclick="openGalleryPreview('${item.id}')">查看全部页面</button></div>`;
  } catch (error) {
    $('#creation-analysis').className = 'analysis-empty';
    $('#creation-analysis').textContent = '分析失败：' + error.message;
  } finally {
    button.disabled = false;
    button.textContent = 'AI 分析并推荐';
  }
}

function ensureCreationRequirement() {
  const ws = activeOrCreateWorkspace();
  let requirement = nodes.find(node => node.id === creationDraft.requirementId && node.kind === 'requirement');
  if (!requirement || workspaceForNode(requirement)?.id !== ws.id) {
    requirement = membersOf(ws).find(node => node.kind === 'requirement');
  }
  if (!requirement) requirement = addMaterialToWorkspace('requirement', { title:'创作需求' }, 0);
  requirement.data.text = $('#creation-prompt').value.trim();
  requirement.data.input_ids = creationDraft.inputs.map(item => item.id);
  requirement.data.attachments = JSON.parse(JSON.stringify(creationDraft.inputs));
  requirement.data.analysis = creationDraft.analysis;
  requirement.title = '创作需求';
  creationDraft.inputs.forEach((item, index) => {
    if (!membersOf(ws).some(node => node.kind === 'source' && node.data.input_id === item.id)) {
      addMaterialToWorkspace('source', {
        title:item.name,
        name:item.name,
        input_id:item.id,
        kind:item.kind,
        mime:item.mime,
        size:item.size,
        excerpt:item.excerpt || '',
      }, membersOf(ws).length + index);
    }
  });
  nodesEl.innerHTML = '';
  nodes.forEach(renderNode);
  save();
  return { ws, requirement };
}

function applyRecommendedRecipe(ws, analysis) {
  const item = analysis.recommended_template;
  if (!membersOf(ws).some(node => node.kind === 'template' && node.data.gallery_id === item.id)) {
    addMaterialToWorkspace('template', galleryTemplateData(item), membersOf(ws).length);
  }
  item.pages.forEach((page, index) => {
    if (!membersOf(ws).some(node => node.kind === 'block' && node.data.gallery_id === item.id && node.data.page_id === page.id)) {
      addMaterialToWorkspace('block', galleryPageData(item, page), membersOf(ws).length + index);
    }
  });
}

async function adoptRecommendedAndGenerate() {
  if (!creationDraft.analysis) return analyzeCreation();
  const { ws, requirement } = ensureCreationRequirement();
  applyRecommendedRecipe(ws, creationDraft.analysis);
  closeCreatePanel();
  focusWorkspace(ws.id);
  await advanceWs(ws.id, { analysis:creationDraft.analysis, selectionMode:'recommended' });
  select(requirement.id);
}

function sendToCustomWorkspace() {
  const { ws, requirement } = ensureCreationRequirement();
  closeCreatePanel();
  focusWorkspace(ws.id);
  document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('on', tab.dataset.tab === 'layouts'));
  activeTab = 'layouts';
  renderPalette();
  select(requirement.id);
  flash('需求已进入工作区：现在可从版式、内容、风格、文件、技能中自由组合，再点“推进生成”', true);
}

$('#create-modal').addEventListener('pointerdown', event => { if (event.target === $('#create-modal')) closeCreatePanel(); });
$('#ai-modal').addEventListener('pointerdown', event => { if (event.target === $('#ai-modal')) closeAISettings(); });
