(() => {
  'use strict';

  const paths = {
    library:'<path d="M4 5.5h6v13H4zM14 5.5h6v13h-6z"/><path d="M6.5 9h1M16.5 9h1"/>',
    inspector:'<path d="M4 6h10M18 6h2M4 12h3M11 12h9M4 18h7M15 18h5"/><circle cx="16" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="13" cy="18" r="2"/>',
    theme:'<path d="M20 15.2A8 8 0 1 1 8.8 4 6.5 6.5 0 0 0 20 15.2Z"/>',
    ai:'<path d="m12 3 1.2 4.1L17 9l-3.8 1.9L12 15l-1.2-4.1L7 9l3.8-1.9L12 3Z"/><path d="m5 14 .8 2.4L8 17.5l-2.2 1.1L5 21l-.8-2.4L2 17.5l2.2-1.1L5 14Z"/>',
    memory:'<ellipse cx="12" cy="5.5" rx="7" ry="3"/><path d="M5 5.5v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6M5 11.5v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>',
    plus:'<path d="M12 5v14M5 12h14"/>',
    play:'<path d="m9 7 8 5-8 5V7Z"/>',
    more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    diagnostic:'<path d="M4 18h16M6 15V9M12 15V5M18 15v-3"/>',
    classic:'<path d="M4 5h16v14H4zM4 9h16M9 9v10"/>',
    install:'<path d="M12 3v12M7 10l5 5 5-5"/><path d="M5 20h14"/>',
    undo:'<path d="M9 7 4 12l5 5"/><path d="M4 12h9a6 6 0 0 1 6 6"/>',
    redo:'<path d="m15 7 5 5-5 5"/><path d="M20 12h-9a6 6 0 0 0-6 6"/>',
    select:'<path d="M4 4h5M4 4v5M20 4h-5M20 4v5M4 20h5M4 20v-5M20 20h-5M20 20v-5"/>',
    group:'<rect x="3.5" y="5" width="9" height="9" rx="1"/><rect x="11.5" y="10" width="9" height="9" rx="1"/>',
    lock:'<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    search:'<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/>',
    zoomIn:'<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5M10.5 7.5v6M7.5 10.5h6"/>',
    zoomOut:'<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5M7.5 10.5h6"/>',
    fit:'<path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/>',
    workspace:'<path d="M4 5h7v6H4zM13 5h7v10h-7zM4 13h7v6H4zM13 17h7v2h-7z"/>',
    collapse:'<path d="m7 14 5-5 5 5"/>',
    expand:'<path d="m7 10 5 5 5-5"/>',
    prompt:'<path d="M5 5h14v11H9l-4 3V5Z"/><path d="M8 9h8M8 12h5"/>',
    file:'<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5"/>',
    image:'<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="10" r="1.5"/><path d="m5 17 5-5 3 3 2-2 4 4"/>',
    content:'<path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5"/>',
    layout:'<path d="M4 4h16v16H4zM4 9h16M10 9v11"/>',
    palette:'<path d="M12 3a9 9 0 1 0 0 18h1.5a2 2 0 0 0 0-4H12a2 2 0 0 1 0-4h3a6 6 0 0 0 0-12h-3Z"/><circle cx="7.5" cy="9" r=".7"/><circle cx="10" cy="6.5" r=".7"/><circle cx="14" cy="6.5" r=".7"/>',
    color:'<circle cx="12" cy="12" r="8"/><path d="M12 4v16M4 12h16"/>',
    type:'<path d="M5 6V4h14v2M12 4v16M8 20h8"/>',
    skill:'<path d="m12 3 7.8 4.5v9L12 21l-7.8-4.5v-9L12 3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/>',
    output:'<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5M9 15l2 2 4-4"/>'
  };

  function hydrateIcon(element) {
    if (!element || element.dataset.iconReady === 'true') return;
    const body = paths[element.dataset.icon];
    if (!body) return;
    element.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">${body}</svg>`;
    element.dataset.iconReady = 'true';
  }

  function hydrate(root = document) {
    if (root.matches?.('[data-icon]')) hydrateIcon(root);
    root.querySelectorAll?.('[data-icon]:not([data-icon-ready="true"])').forEach(hydrateIcon);
  }

  function syncMenuState() {
    document.querySelectorAll('.topbar-more').forEach(details => {
      details.querySelector('summary')?.setAttribute('aria-expanded', String(details.open));
    });
  }

  hydrate();
  syncMenuState();

  const observer = new MutationObserver(records => {
    for (const record of records) for (const node of record.addedNodes) if (node.nodeType === Node.ELEMENT_NODE) hydrate(node);
  });
  observer.observe(document.body, {childList:true, subtree:true});

  document.addEventListener('toggle', event => {
    if (event.target.matches?.('.topbar-more')) syncMenuState();
  }, true);
  document.addEventListener('click', event => {
    const action = event.target.closest('.topbar-menu button,.topbar-menu a');
    if (action) action.closest('.topbar-more')?.removeAttribute('open');
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') document.querySelectorAll('.topbar-more[open]').forEach(details => details.removeAttribute('open'));
  });

  const nodeIcons = {requirement:'prompt',source:'file',block:'content',template:'layout',style:'palette',color:'color',font:'type',skill:'skill',file:'file',output:'output'};
  function renderMobileTaskView() {
    const host = document.querySelector('#mobile-task-view');
    if (!host || innerWidth > 620 || typeof nodes === 'undefined') return;
    const workspaces = nodes.filter(node => node.kind === 'ws');
    const workspace = workspaces.find(node => node.id === activeWorkspaceId) || workspaces[0];
    if (!workspace) {
      host.innerHTML = `<div class="mobile-task-empty">当前还没有工作区。使用顶部“输入需求”开始创作。</div>`;
      return;
    }
    const members = nodes.filter(node => node.workspaceId === workspace.id && node.kind !== 'ws');
    const outputCount = members.filter(node => node.kind === 'output').length;
    const tabs = workspaces.length > 1 ? `<div class="mobile-workspace-tabs">${workspaces.map(item => `<button type="button" class="${item.id === workspace.id ? 'active' : ''}" data-mobile-workspace="${item.id}">${esc(item.title)}</button>`).join('')}</div>` : '';
    const cards = members.length ? members.map(node => {
      const state = node.kind === 'output' ? `rev${node.data?.revision || 0}` : kindLabel(node.kind);
      return `<button type="button" class="mobile-task-card" data-mobile-node="${node.id}"><span class="task-icon"><span class="ui-icon" data-icon="${nodeIcons[node.kind] || 'content'}" aria-hidden="true"></span></span><span><strong>${esc(node.data?.title || node.title || kindLabel(node.kind))}</strong><small>${esc(kindLabel(node.kind))} · 点按查看和编辑</small></span><span class="task-state">${esc(state)}</span></button>`;
    }).join('') : `<div class="mobile-task-empty">工作区中还没有素材。打开素材库，或先输入需求。</div>`;
    host.innerHTML = `${tabs}<div class="mobile-task-head"><span class="mobile-task-eyebrow">当前工作区</span><h2>${esc(workspace.title)}</h2><p>${members.length} 个节点 · ${outputCount} 个产物</p></div><div class="mobile-task-actions"><button type="button" class="btn btn-secondary" data-mobile-create><span class="ui-icon" data-icon="plus" aria-hidden="true"></span>输入需求</button><button type="button" class="btn btn-primary" data-mobile-advance><span class="ui-icon" data-icon="play" aria-hidden="true"></span>推进工作区</button></div><div class="mobile-task-list">${cards}</div>`;
    hydrate(host);
    host.querySelector('[data-mobile-create]')?.addEventListener('click', () => openCreatePanel());
    host.querySelector('[data-mobile-advance]')?.addEventListener('click', () => advanceWs(workspace.id));
    host.querySelectorAll('[data-mobile-workspace]').forEach(button => button.addEventListener('click', () => {
      activeWorkspaceId = Number(button.dataset.mobileWorkspace);
      renderWorkspaceNavigator(); timeline(); renderMobileTaskView();
    }));
    host.querySelectorAll('[data-mobile-node]').forEach(button => button.addEventListener('click', () => {
      select(Number(button.dataset.mobileNode));
      toggleMobilePanel('inspector');
    }));
  }

  const taskSources = [document.querySelector('#nodes'), document.querySelector('#workspace-list')].filter(Boolean);
  const taskObserver = new MutationObserver(() => setTimeout(renderMobileTaskView, 0));
  taskSources.forEach(source => taskObserver.observe(source, {childList:true, subtree:true}));
  setTimeout(renderMobileTaskView, 160);

  let viewportBand = innerWidth <= 620 ? 'mobile' : innerWidth <= 900 ? 'tablet' : 'desktop';
  let resizeTimer = null;
  function fitResponsiveCanvas(force = false) {
    const nextBand = innerWidth <= 620 ? 'mobile' : innerWidth <= 900 ? 'tablet' : 'desktop';
    if (!force && nextBand === viewportBand) return;
    viewportBand = nextBand;
    renderMobileTaskView();
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      window.closeMobilePanels?.();
      if (nextBand !== 'desktop' && typeof window.fitAll === 'function') window.fitAll(false);
    }, 80);
  }
  window.addEventListener('resize', () => fitResponsiveCanvas(false));
  if (viewportBand !== 'desktop') setTimeout(() => fitResponsiveCanvas(true), 140);

  window.FoxWorkbenchUI = { hydrate, fitResponsiveCanvas, renderMobileTaskView };
})();