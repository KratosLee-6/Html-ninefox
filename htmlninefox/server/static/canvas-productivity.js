(() => {
  'use strict';

  const history = [];
  let historyIndex = -1;
  let historyTimer = null;
  let initialized = false;
  let applyingHistory = false;
  let selectionMode = false;
  let lasso = null;
  let minimapFrame = null;
  let minimapMap = null;
  let commandResults = [];
  let commandIndex = 0;
  let commandListenersReady = false;
  let commandsRegistered = false;

  const clone = value => JSON.parse(JSON.stringify(value));
  const selectedNodes = () => nodes.filter(node => selectedIds.has(node.id));
  const editableTarget = target => Boolean(target?.closest?.('textarea,input,select,[contenteditable="true"]'));

  function historyPayload() {
    return { nodes, edges, groups, uid, wsSeq, activeWorkspaceId, workspaceNavigatorCollapsed };
  }

  function historySignature() {
    return JSON.stringify(historyPayload());
  }

  function updateToolbar() {
    const undoButton = document.getElementById('canvas-undo');
    const redoButton = document.getElementById('canvas-redo');
    const groupButton = document.getElementById('canvas-group');
    const lockButton = document.getElementById('canvas-lock');
    const selectButton = document.getElementById('canvas-select-mode');
    if (undoButton) undoButton.disabled = historyIndex <= 0;
    if (redoButton) redoButton.disabled = historyIndex < 0 || historyIndex >= history.length - 1;
    if (groupButton) groupButton.disabled = selectedIds.size < 2;
    if (lockButton) {
      lockButton.disabled = selectedIds.size === 0;
      const items = selectedNodes();
      const allLocked = items.length > 0 && items.every(node => node.locked);
      lockButton.textContent = allLocked ? '解' : '锁';
      lockButton.title = allLocked ? '解锁所选节点' : '锁定所选节点';
    }
    if (selectButton) selectButton.classList.toggle('on', selectionMode);
  }

  function commitHistory() {
    clearTimeout(historyTimer);
    historyTimer = null;
    if (!initialized || applyingHistory) return;
    const signature = historySignature();
    if (history[historyIndex]?.signature === signature) {
      updateToolbar();
      return;
    }
    history.splice(historyIndex + 1);
    history.push({ signature, snapshot:clone(workspaceSnapshot()) });
    if (history.length > 80) history.shift();
    historyIndex = history.length - 1;
    updateToolbar();
  }

  function scheduleHistory(immediate = false) {
    scheduleMinimap();
    if (!initialized || applyingHistory) return;
    clearTimeout(historyTimer);
    if (immediate) commitHistory();
    else historyTimer = setTimeout(commitHistory, 280);
  }

  function initialize() {
    history.length = 0;
    historyIndex = -1;
    initialized = true;
    history.push({ signature:historySignature(), snapshot:clone(workspaceSnapshot()) });
    historyIndex = 0;
    updateSelectionUI();
    updateToolbar();
    registerWorkbenchCommands();
    prepareCommandPalette();
    scheduleMinimap();
  }

  function restore(entry) {
    if (!entry) return;
    applyingHistory = true;
    clearTimeout(historyTimer);
    historyTimer = null;
    const currentCamera = { ...camera };
    const currentSnapLevel = snapLevel;
    applyWorkspaceSnapshot(clone(entry.snapshot));
    camera = currentCamera;
    snapLevel = currentSnapLevel;
    selectedIds.clear();
    selected = null;
    nodesEl.innerHTML = '';
    nodes.forEach(renderNode);
    drawEdges();
    applyCamera(false);
    updateWsCount();
    renderWorkspaceNavigator();
    timeline();
    renderInspector();
    save();
    applyingHistory = false;
    updateToolbar();
    scheduleMinimap();
  }

  function undo() {
    commitHistory();
    if (historyIndex <= 0) return;
    historyIndex -= 1;
    restore(history[historyIndex]);
    flash('已撤销上一步画布操作', true);
  }

  function redo() {
    commitHistory();
    if (historyIndex >= history.length - 1) return;
    historyIndex += 1;
    restore(history[historyIndex]);
    flash('已重做画布操作', true);
  }

  function updateSelectionUI() {
    document.querySelectorAll('.node').forEach(element => {
      const id = Number(element.dataset.id);
      const node = nodes.find(item => item.id === id);
      element.classList.toggle('selected', selectedIds.has(id));
      element.classList.toggle('locked', Boolean(node?.locked));
      element.classList.toggle('grouped', Boolean(node?.groupId));
      if (node?.groupId) element.dataset.groupId = node.groupId;
      else delete element.dataset.groupId;
    });
    if (selected != null && !selectedIds.has(selected)) selected = [...selectedIds].at(-1) ?? null;
    updateToolbar();
    scheduleMinimap();
  }

  function nodesWithin(rect, contained = rect.x2 >= rect.x1) {
    const minX = Math.min(rect.x1, rect.x2);
    const minY = Math.min(rect.y1, rect.y2);
    const maxX = Math.max(rect.x1, rect.x2);
    const maxY = Math.max(rect.y1, rect.y2);
    return nodes.filter(node => node.kind !== 'ws').filter(node => {
      const size = canvasEngine.nodeSize(node);
      const left = node.x, top = node.y, right = node.x + size.width, bottom = node.y + size.height;
      return contained
        ? left >= minX && right <= maxX && top >= minY && bottom <= maxY
        : left < maxX && right > minX && top < maxY && bottom > minY;
    });
  }

  function clearSelectionPreview() {
    document.querySelectorAll('.node.selection-preview').forEach(element => element.classList.remove('selection-preview'));
  }

  function previewWithin(rect, contained) {
    const hits = nodesWithin(rect, contained);
    const hitIds = new Set(hits.map(node => node.id));
    document.querySelectorAll('.node[id]').forEach(element => {
      const id = Number(element.id.replace('node-', ''));
      element.classList.toggle('selection-preview', hitIds.has(id));
    });
    return hits;
  }

  function selectWithin(rect, additive = false, options = {}) {
    const contained = options.contained ?? false;
    const hits = nodesWithin(rect, contained).map(node => node.id);
    if (options.subtract) selectMany([...selectedIds].filter(id => !hits.includes(id)));
    else selectMany(hits, { additive });
    return hits;
  }

  function toggleSelectionMode() {
    selectionMode = !selectionMode;
    viewport.classList.toggle('selection-mode', selectionMode);
    updateToolbar();
    flash(selectionMode ? '框选已开启：左→右完整包含，右→左触碰即选；Alt 可减选' : '已返回画布平移模式', true);
  }

  function isSelectionMode() {
    return selectionMode;
  }

  function beginLasso(event) {
    if (!(selectionMode || event.shiftKey)) return false;
    const point = toWorld(event);
    lasso = {
      pointerId:event.pointerId,
      x1:point[0], y1:point[1], x2:point[0], y2:point[1],
      clientX:event.clientX, clientY:event.clientY,
      additive:event.ctrlKey || event.metaKey || event.shiftKey,
      subtract:event.altKey, contained:true,
    };
    const box = document.getElementById('selection-box');
    box.hidden = false;
    box.dataset.count = '0';
    box.dataset.mode = '完整包含';
    box.style.left = point[0] + 'px';
    box.style.top = point[1] + 'px';
    box.style.width = '0px';
    box.style.height = '0px';
    return true;
  }

  function moveLasso(event) {
    if (!lasso) return false;
    const point = toWorld(event);
    lasso.x2 = point[0];
    lasso.y2 = point[1];
    lasso.lastClientX = event.clientX;
    lasso.lastClientY = event.clientY;
    lasso.contained = lasso.x2 >= lasso.x1;
    const box = document.getElementById('selection-box');
    box.style.left = Math.min(lasso.x1, lasso.x2) + 'px';
    box.style.top = Math.min(lasso.y1, lasso.y2) + 'px';
    box.style.width = Math.abs(lasso.x2 - lasso.x1) + 'px';
    box.style.height = Math.abs(lasso.y2 - lasso.y1) + 'px';
    box.dataset.mode = lasso.contained ? '完整包含' : '触碰即选';
    const hits = previewWithin(lasso, lasso.contained);
    box.dataset.count = String(hits.length);
    return true;
  }

  function finishLasso() {
    if (!lasso) return false;
    const current = lasso;
    lasso = null;
    const box = document.getElementById('selection-box');
    box.hidden = true;
    clearSelectionPreview();
    const screenDistance = Math.hypot((current.lastClientX ?? current.clientX) - current.clientX,
      (current.lastClientY ?? current.clientY) - current.clientY);
    if (screenDistance < 5) {
      if (!current.additive && !current.subtract) select(null);
      return true;
    }
    const hits = selectWithin(current, current.additive, { contained:current.contained, subtract:current.subtract });
    const verb = current.subtract ? '减选' : current.contained ? '完整框选' : '触碰框选';
    flash(verb + ' ' + hits.length + ' 个节点', true);
    return true;
  }

  function dragMembers(node) {
    if (node.kind === 'ws') {
      return [node, ...membersOf(node, { includeOutputs:true })].filter(item => !item.locked);
    }
    if (node.groupId) return nodes.filter(item => item.groupId === node.groupId && !item.locked);
    const chosen = selectedIds.has(node.id) && selectedIds.size > 1 ? selectedNodes() : [node];
    return chosen.filter(item => item.kind !== 'ws' && !item.locked);
  }

  function groupSelection() {
    const items = selectedNodes().filter(node => node.kind !== 'ws');
    if (items.length < 2) return flash('至少选择两个素材节点才能组合', false);
    const workspaces = new Set(items.map(node => workspaceForNode(node)?.id ?? null));
    if (workspaces.size > 1) return flash('只能组合位于同一工作区的素材', false);
    const groupId = 'group-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6);
    items.forEach(node => { node.groupId = groupId; });
    updateSelectionUI();
    window.FoxCanvasGroups?.sync();   /* G7：同步建立可视化组框容器 */
    renderInspector();
    save();
    scheduleHistory(true);
    flash('已组合 ' + items.length + ' 个节点', true);
  }

  function ungroupSelection() {
    const groupIds = new Set(selectedNodes().map(node => node.groupId).filter(Boolean));
    if (!groupIds.size) return flash('所选节点尚未组合', false);
    nodes.forEach(node => { if (groupIds.has(node.groupId)) node.groupId = null; });
    updateSelectionUI();
    window.FoxCanvasGroups?.sync();   /* G7：移除容器与组记录 */
    renderInspector();
    save();
    scheduleHistory(true);
    flash('已取消组合', true);
  }

  function toggleLockSelection() {
    const items = selectedNodes();
    if (!items.length) return;
    const shouldLock = !items.every(node => node.locked);
    items.forEach(node => { node.locked = shouldLock; });
    updateSelectionUI();
    renderInspector();
    save();
    scheduleHistory(true);
    flash(shouldLock ? '已锁定所选节点' : '已解锁所选节点', true);
  }

  function renderSelectionInspector(box) {
    const items = selectedNodes();
    if (items.length < 2) return false;
    const groupIds = new Set(items.map(node => node.groupId).filter(Boolean));
    const locked = items.filter(node => node.locked).length;
    const workspaceCount = new Set(items.map(node => workspaceForNode(node)?.title || '画布')).size;
    box.innerHTML = `<h3>多选 · ${items.length} 个节点</h3>
      <div class="field"><div class="kv"><span>所在工作区</span><span>${workspaceCount}</span></div>
      <div class="kv"><span>组合</span><span>${groupIds.size ? groupIds.size + ' 组' : '未组合'}</span></div>
      <div class="kv"><span>锁定</span><span>${locked} / ${items.length}</span></div></div>
      <div class="field selection-actions"><button class="btn btn-secondary" onclick="FoxCanvasProductivity.groupSelection()">组合</button>
      <button class="btn btn-secondary" onclick="FoxCanvasProductivity.ungroupSelection()">取消组合</button>
      <button class="btn btn-secondary" onclick="FoxCanvasProductivity.toggleLockSelection()">${locked === items.length ? '解锁' : '锁定'}</button></div>
      <button class="btn btn-danger-ghost" onclick="FoxCanvasProductivity.deleteSelection()">删除所选节点</button>
      <p class="ins-empty" style="margin-top:10px">拖动任一所选节点可整体移动；按 Shift 点击可继续增减选择。</p>`;
    return true;
  }

  function deleteSelection() {
    const ids = [...selectedIds];
    if (!ids.length) return;
    deleteNodeIds(ids);
    scheduleHistory(true);
    flash('已删除 ' + ids.length + ' 个画布节点', true);
  }

  function nodeBounds() {
    if (!nodes.length) return { x:0, y:0, width:1, height:1 };
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const node of nodes) {
      const size = canvasEngine.nodeSize(node);
      minX = Math.min(minX, node.x);
      minY = Math.min(minY, node.y);
      maxX = Math.max(maxX, node.x + size.width);
      maxY = Math.max(maxY, node.y + size.height);
    }
    const view = {
      x:-camera.x / camera.z,
      y:-camera.y / camera.z,
      width:viewport.clientWidth / camera.z,
      height:viewport.clientHeight / camera.z,
    };
    minX = Math.min(minX, view.x);
    minY = Math.min(minY, view.y);
    maxX = Math.max(maxX, view.x + view.width);
    maxY = Math.max(maxY, view.y + view.height);
    return {
      x:minX - 80,
      y:minY - 80,
      width:Math.max(1, maxX - minX + 160),
      height:Math.max(1, maxY - minY + 160),
    };
  }

  function renderMinimap() {
    minimapFrame = null;
    const svg = document.getElementById('minimap-svg');
    if (!svg) return;
    const bounds = nodeBounds();
    const width = 184;
    const height = 116;
    const scale = Math.min(width / bounds.width, height / bounds.height);
    const offsetX = (width - bounds.width * scale) / 2;
    const offsetY = (height - bounds.height * scale) / 2;
    minimapMap = { bounds, scale, offsetX, offsetY };
    const mapX = value => offsetX + (value - bounds.x) * scale;
    const mapY = value => offsetY + (value - bounds.y) * scale;
    const nodeRects = nodes.map(node => {
      const size = canvasEngine.nodeSize(node);
      const color = node.kind === 'ws' ? (node.data?.color || '#5B8DEF') : selectedIds.has(node.id) ? '#E57A3F' : '#718B80';
      return `<rect class="minimap-node ${node.kind}" x="${mapX(node.x).toFixed(1)}" y="${mapY(node.y).toFixed(1)}" width="${Math.max(2, size.width * scale).toFixed(1)}" height="${Math.max(2, size.height * scale).toFixed(1)}" fill="${color}"/>`;
    }).join('');
    const viewX = -camera.x / camera.z;
    const viewY = -camera.y / camera.z;
    const viewWidth = viewport.clientWidth / camera.z;
    const viewHeight = viewport.clientHeight / camera.z;
    svg.innerHTML = nodeRects + `<rect class="minimap-viewport" x="${mapX(viewX).toFixed(1)}" y="${mapY(viewY).toFixed(1)}" width="${Math.max(4, viewWidth * scale).toFixed(1)}" height="${Math.max(4, viewHeight * scale).toFixed(1)}"/>`;
  }

  function scheduleMinimap() {
    if (minimapFrame) return;
    minimapFrame = requestAnimationFrame(renderMinimap);
  }

  function navigateMinimap(event) {
    if (!minimapMap) return;
    const svg = document.getElementById('minimap-svg');
    const rect = svg.getBoundingClientRect();
    const svgX = (event.clientX - rect.left) / rect.width * 184;
    const svgY = (event.clientY - rect.top) / rect.height * 116;
    const worldX = minimapMap.bounds.x + (svgX - minimapMap.offsetX) / minimapMap.scale;
    const worldY = minimapMap.bounds.y + (svgY - minimapMap.offsetY) / minimapMap.scale;
    camera.x = viewport.clientWidth / 2 - worldX * camera.z;
    camera.y = viewport.clientHeight / 2 - worldY * camera.z;
    applyCamera(true, true);
  }

  function registerWorkbenchCommands() {
    if (commandsRegistered || !window.FoxInteraction) return;
    commandsRegistered = true;
    const register = command => window.FoxInteraction.registerCommand(command);
    const clickControl = id => {
      const control = document.getElementById(id);
      control?.focus();
      control?.click();
    };
    register({ id:'create-input', label:'输入需求与素材', description:'添加文字、文件或图片并开始 AI 分析', keywords:['创作','附件','图片','文件'], shortcut:'I', run:() => clickControl('btn-create') });
    register({ id:'advance', label:'推进当前工作区生成', description:'分析需求、组合素材并生成产物', keywords:['生成','运行','工作流'], shortcut:'G', run:() => clickControl('btn-go') });
    register({ id:'new-workspace', label:'新建工作区', description:'在当前视图中心创建独立工作区', keywords:['画布','项目'], shortcut:'W', run:() => addWorkspace() });
    register({ id:'ai-settings', label:'打开 AI 模型配置', description:'配置兼容接口、模型名称与 API Key', keywords:['模型','key','接口'], run:() => clickControl('btn-ai-settings') });
    register({ id:'diagnostic', label:'生成脱敏诊断包', description:'收集本地运行信息用于故障定位', keywords:['日志','排错'], run:() => clickControl('btn-diagnostic') });
    register({ id:'toggle-theme', label:'切换主题', description:'在纸白与夜蓝像素花园之间切换', keywords:['颜色','皮肤','深色'], run:() => clickControl('btn-theme') });
    register({ id:'undo', label:'撤销画布操作', description:'恢复上一步节点或工作区变化', shortcut:'Ctrl Z', isEnabled:() => historyIndex > 0, run:undo });
    register({ id:'redo', label:'重做画布操作', description:'恢复刚刚撤销的变化', shortcut:'Ctrl Y', isEnabled:() => historyIndex >= 0 && historyIndex < history.length - 1, run:redo });
    register({ id:'selection-mode', label:'切换框选模式', description:'拖动画布批量选择节点', keywords:['多选','框选'], run:toggleSelectionMode });
    register({ id:'fit-all', label:'适配全部内容', description:'自动缩放并居中所有画布节点', keywords:['定位','缩放','居中'], run:fitAll });
  }

  function commandItems(query = '') {
    const normalized = query.trim().toLowerCase();
    const actions = (window.FoxInteraction?.searchCommands(query) || []).map(command => ({ type:'command', command }));
    const canvasNodes = nodes.filter(node => {
      const haystack = [node.title, node.data?.title, node.data?.name, kindLabel(node.kind), workspaceForNode(node)?.title]
        .filter(Boolean).join(' ').toLowerCase();
      return !normalized || haystack.includes(normalized);
    }).slice(0, normalized ? 30 : 12).map(node => ({ type:'node', node }));
    return [...actions, ...canvasNodes];
  }

  function commandResultMarkup(item, index) {
    if (item.type === 'command') {
      const command = item.command;
      return `<button type="button" id="command-option-${index}" role="option" data-command-id="${esc(command.id)}" data-command-index="${index}"><span class="command-result-main"><b>${esc(command.label)}</b><small>${esc(command.description || command.group)}</small></span>${command.shortcut ? `<kbd class="command-shortcut">${esc(command.shortcut)}</kbd>` : '<span></span>'}</button>`;
    }
    const node = item.node;
    return `<button type="button" id="command-option-${index}" role="option" data-canvas-result="${node.id}" data-command-index="${index}"><span class="command-result-main"><b>${esc(node.title || kindLabel(node.kind))}</b><small>${esc(kindLabel(node.kind))} · ${esc(workspaceForNode(node)?.title || '画布')}</small></span><kbd class="command-shortcut">定位</kbd></button>`;
  }

  function updateCommandSelection(nextIndex = commandIndex) {
    const list = document.getElementById('canvas-command-results');
    const input = document.getElementById('canvas-command-input');
    if (!list || !commandResults.length) {
      commandIndex = 0;
      input?.removeAttribute('aria-activedescendant');
      return;
    }
    commandIndex = (nextIndex + commandResults.length) % commandResults.length;
    list.querySelectorAll('[data-command-index]').forEach(button => {
      const active = Number(button.dataset.commandIndex) === commandIndex;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', String(active));
      if (active) {
        input?.setAttribute('aria-activedescendant', button.id);
        button.scrollIntoView({ block:'nearest' });
      }
    });
  }

  function renderCommandResults() {
    const input = document.getElementById('canvas-command-input');
    const list = document.getElementById('canvas-command-results');
    if (!input || !list) return;
    commandResults = commandItems(input.value);
    commandIndex = 0;
    if (!commandResults.length) {
      list.innerHTML = '<div class="command-empty">没有匹配的操作或节点</div>';
      updateCommandSelection();
      return;
    }
    const actionCount = commandResults.filter(item => item.type === 'command').length;
    const nodeCount = commandResults.length - actionCount;
    const actions = commandResults.slice(0, actionCount).map((item, index) => commandResultMarkup(item, index)).join('');
    const canvasNodes = commandResults.slice(actionCount).map((item, index) => commandResultMarkup(item, actionCount + index)).join('');
    list.innerHTML = `
      ${actions ? '<div class="command-section-label">操作</div>' + actions : ''}
      ${canvasNodes ? '<div class="command-section-label">节点</div>' + canvasNodes : ''}`;
    list.querySelectorAll('[data-command-index]').forEach(button => {
      button.addEventListener('mouseenter', () => updateCommandSelection(Number(button.dataset.commandIndex)));
      button.addEventListener('click', () => activateCommandResult(Number(button.dataset.commandIndex)));
    });
    updateCommandSelection(0);
  }

  function activateCommandResult(index = commandIndex) {
    const item = commandResults[index];
    if (!item) return;
    if (item.type === 'command') {
      closeSearch();
      window.FoxInteraction?.runCommand(item.command.id, { source:'palette' });
    } else {
      focusNode(item.node.id);
    }
  }

  function handleCommandKeydown(event) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      updateCommandSelection(commandIndex + 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      updateCommandSelection(commandIndex - 1);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      activateCommandResult();
    }
  }

  function prepareCommandPalette() {
    if (commandListenersReady) return;
    commandListenersReady = true;
    const modal = document.getElementById('canvas-command');
    const input = document.getElementById('canvas-command-input');
    input?.addEventListener('input', renderCommandResults);
    input?.addEventListener('keydown', handleCommandKeydown);
    modal?.addEventListener('pointerdown', event => {
      if (event.target === modal) closeSearch();
    });
    window.FoxInteraction?.registerDialog(modal, { onRequestClose:closeSearch, initialFocus:'#canvas-command-input' });
  }

  function openSearch() {
    const modal = document.getElementById('canvas-command');
    const input = document.getElementById('canvas-command-input');
    prepareCommandPalette();
    input.value = '';
    renderCommandResults();
    window.FoxInteraction?.openDialog(modal, { initialFocus:'#canvas-command-input' });
  }

  function closeSearch() {
    window.FoxInteraction?.closeDialog('#canvas-command');
  }

  function focusNode(id) {
    const node = nodes.find(item => item.id === id);
    if (!node) return;
    const size = canvasEngine.nodeSize(node);
    select(id);
    fitRect(node.x, node.y, size.width, size.height, 180);
    closeSearch();
  }

  document.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      openSearch();
      return;
    }
    if (!editableTarget(event.target) && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
      event.preventDefault();
      if (event.shiftKey) redo();
      else undo();
      return;
    }
    if (!editableTarget(event.target) && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'y') {
      event.preventDefault();
      redo();
      return;
    }
    if (event.key === 'Escape') {
      closeSearch();
      if (selectionMode) toggleSelectionMode();
    }
  });

  window.FoxCanvasProductivity = {
    initialize,
    scheduleHistory,
    commitHistory,
    undo,
    redo,
    updateSelectionUI,
    selectWithin,
    toggleSelectionMode,
    isSelectionMode,
    beginLasso,
    moveLasso,
    finishLasso,
    dragMembers,
    groupSelection,
    ungroupSelection,
    toggleLockSelection,
    renderSelectionInspector,
    deleteSelection,
    scheduleMinimap,
    navigateMinimap,
    openSearch,
    closeSearch,
    renderCommandResults,
    focusNode,
  };
})();
