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

  const clone = value => JSON.parse(JSON.stringify(value));
  const selectedNodes = () => nodes.filter(node => selectedIds.has(node.id));
  const editableTarget = target => Boolean(target?.closest?.('textarea,input,select,[contenteditable="true"]'));

  function historyPayload() {
    return { nodes, edges, uid, wsSeq, activeWorkspaceId, workspaceNavigatorCollapsed };
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
    scheduleMinimap();
  }

  function restore(entry) {
    if (!entry) return;
    applyingHistory = true;
    clearTimeout(historyTimer);
    historyTimer = null;
    const currentCamera = { ...camera };
    applyWorkspaceSnapshot(clone(entry.snapshot));
    camera = currentCamera;
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

  function selectWithin(rect, additive = false) {
    const minX = Math.min(rect.x1, rect.x2);
    const minY = Math.min(rect.y1, rect.y2);
    const maxX = Math.max(rect.x1, rect.x2);
    const maxY = Math.max(rect.y1, rect.y2);
    const hits = nodes.filter(node => node.kind !== 'ws').filter(node => {
      const size = canvasEngine.nodeSize(node);
      return node.x < maxX && node.x + size.width > minX && node.y < maxY && node.y + size.height > minY;
    }).map(node => node.id);
    selectMany(hits, { additive });
    return hits;
  }

  function toggleSelectionMode() {
    selectionMode = !selectionMode;
    viewport.classList.toggle('selection-mode', selectionMode);
    updateToolbar();
    flash(selectionMode ? '框选工具已开启：拖动画布空白区域选择节点' : '已返回画布平移模式', true);
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
      additive:event.ctrlKey || event.metaKey || event.shiftKey,
    };
    const box = document.getElementById('selection-box');
    box.hidden = false;
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
    const box = document.getElementById('selection-box');
    box.style.left = Math.min(lasso.x1, lasso.x2) + 'px';
    box.style.top = Math.min(lasso.y1, lasso.y2) + 'px';
    box.style.width = Math.abs(lasso.x2 - lasso.x1) + 'px';
    box.style.height = Math.abs(lasso.y2 - lasso.y1) + 'px';
    return true;
  }

  function finishLasso() {
    if (!lasso) return false;
    const current = lasso;
    lasso = null;
    const box = document.getElementById('selection-box');
    box.hidden = true;
    const distance = Math.hypot(current.x2 - current.x1, current.y2 - current.y1);
    if (distance < 4) {
      if (!current.additive) select(null);
      return true;
    }
    const hits = selectWithin(current, current.additive);
    flash('已框选 ' + hits.length + ' 个节点', true);
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
    applyCamera();
  }

  function commandItems(query = '') {
    const normalized = query.trim().toLowerCase();
    return nodes.filter(node => {
      const haystack = [node.title, node.data?.title, node.data?.name, kindLabel(node.kind), workspaceForNode(node)?.title]
        .filter(Boolean).join(' ').toLowerCase();
      return !normalized || haystack.includes(normalized);
    }).slice(0, 30);
  }

  function renderCommandResults() {
    const input = document.getElementById('canvas-command-input');
    const list = document.getElementById('canvas-command-results');
    if (!input || !list) return;
    const items = commandItems(input.value);
    list.innerHTML = items.map(node => `<button type="button" data-canvas-result="${node.id}"><span>${esc(node.title || kindLabel(node.kind))}</span><small>${esc(kindLabel(node.kind))} · ${esc(workspaceForNode(node)?.title || '画布')}</small></button>`).join('') || '<div class="command-empty">没有匹配的节点</div>';
    list.querySelectorAll('[data-canvas-result]').forEach(button => {
      button.addEventListener('click', () => focusNode(Number(button.dataset.canvasResult)));
    });
  }

  function openSearch() {
    const modal = document.getElementById('canvas-command');
    const input = document.getElementById('canvas-command-input');
    modal.hidden = false;
    input.value = '';
    renderCommandResults();
    requestAnimationFrame(() => input.focus());
  }

  function closeSearch() {
    const modal = document.getElementById('canvas-command');
    if (modal) modal.hidden = true;
  }

  function focusNode(id) {
    const node = nodes.find(item => item.id === id);
    if (!node) return;
    const size = canvasEngine.nodeSize(node);
    select(id);
    fitRect(node.x, node.y, size.width, size.height, 180);
    closeSearch();
  }

  document.getElementById('canvas-command')?.addEventListener('pointerdown', event => {
    if (event.target.id === 'canvas-command') closeSearch();
  });

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
