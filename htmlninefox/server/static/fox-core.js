/* fox-core.js · front-end kernel, extracted from index.html verbatim
 *
 * Do not "tidy" this file. Every character matters: it was moved out of an
 * inline <script> so that tests can load it, and the move was verified
 * byte-for-byte. Behaviour must stay identical, so any edit here is a
 * behaviour change until proven otherwise by tests/test_frontend_kernel_loadable.py
 * and the mutation run in scripts/mutate_frontend_kernel_gates.py.
 *
 * Sections, in order: state & constants, camera, nodes, edges, groups,
 * workspaces, inspector, palette, recipe progress, data loading & init.
 */

/* ============================================================
   迷你线框预览（全可视化素材的核心：图形优先，文字最少）
   ============================================================ */
const B = (x,y,w,h,cls='') => `<i class="${cls}" style="left:${x}%;top:${y}%;width:${w}%;height:${h}%"></i>`;
const MINI = {
  hero:    B(12,22,50,14,'a') + B(12,44,64,7) + B(12,58,40,7) + B(12,74,15,12,'a') + B(30,74,15,12,''),
  feats:   B(8,14,24,60) + B(38,14,24,60) + B(68,14,24,60) + B(12,22,16,6,'a') + B(42,22,16,6,'a') + B(72,22,16,6,'a'),
  pricing: B(10,16,24,66) + B(38,10,24,78,'') + B(66,16,24,66) + B(44,24,12,8,'a') + B(16,40,12,6) + B(44,40,12,6) + B(72,40,12,6),
  faq:     B(8,12,84,16,'') + B(8,36,84,16,'') + B(8,60,84,16,'') + B(84,16,4,8,'a') + B(84,40,4,8,'a') + B(84,64,4,8,'a'),
  kpi:     B(6,18,20,58,'') + B(29,18,20,58,'') + B(52,18,20,58,'') + B(75,18,20,58,'') + B(9,30,8,8,'g') + B(32,30,8,8,'g') + B(55,30,8,8,'m') + B(78,30,8,8,'g'),
  chart:   B(8,58,9,26,'a') + B(20,46,9,38) + B(32,54,9,30) + B(44,32,9,52,'a') + B(56,40,9,44) + B(68,18,9,66,'c') + B(80,28,9,56),
  table:   B(6,12,88,14,'b') + B(6,32,88,12) + B(6,50,88,12) + B(6,68,88,12) + B(74,34,16,8,'y') + B(74,70,16,8,'g'),
  cover:   B(20,30,60,16,'a') + B(30,56,40,7) + B(42,72,16,6),
  quote:   B(14,40,72,12,'a') + B(30,62,40,6),
  road:    B(6,46,10,10,'a') + B(32,46,10,10,'a') + B(58,46,10,10,'a') + B(84,46,10,10,'') + B(16,50,16,2,'a') + B(42,50,16,2,'a') + B(68,50,16,2),
  layers:  B(10,10,80,16) + B(10,32,80,16) + B(10,54,80,16) + B(10,76,80,14,'a'),
  cta:     B(0,30,100,40,'a') + B(14,46,40,10) + B(72,44,16,14),
};
const PAGE_MINI = {
  landing:   B(8,8,84,20,'a') + B(8,36,26,30) + B(38,36,26,30) + B(68,36,26,30) + B(8,74,50,10) + B(8,88,20,8,'a'),
  dashboard: B(8,8,19,26) + B(30,8,19,26) + B(52,8,19,26) + B(74,8,19,26) + B(8,42,54,34) + B(66,42,27,34) + B(8,82,84,12),
  deck:      B(8,8,84,66) + B(16,30,50,14,'a') + B(16,52,34,8) + B(8,80,6,8,'a') + B(20,80,6,8) + B(32,80,6,8) + B(86,80,6,8),
  poster:    B(10,10,60,26,'a') + B(10,42,44,10) + B(10,60,26,12) + B(42,60,26,12) + B(74,60,16,12) + B(10,82,80,12,'m'),
  archdoc:   B(8,8,50,12,'a') + B(8,26,84,12) + B(8,42,84,12) + B(8,58,84,12) + B(8,74,84,12) + B(8,90,40,6),
  doc:       B(26,8,48,12,'a') + B(8,30,84,16) + B(8,54,38,10) + B(54,54,38,10) + B(8,70,84,6) + B(8,80,84,6) + B(8,90,30,6),
};
const FONTS = [
  { id:'sans',  t:'无衬线',   en:'Inter · Sans',   aa:'Aa', css:"'Inter','PingFang SC',sans-serif" },
  { id:'serif', t:'衬线 · 杂志', en:'Georgia · Serif', aa:'Aa', css:"'Georgia','Noto Serif SC',serif" },
  { id:'mono',  t:'等宽 · 极客', en:'JetBrains Mono', aa:'Aa', css:"'JetBrains Mono',Consolas,monospace" },
];
const COLORS = [
  { id:'garden', t:'像素花园', en:'#173C8F', hex:'#173C8F', sw:['#FFFDF6','#173C8F','#49B894'] },
  { id:'mint',   t:'薄荷苗圃', en:'#49B894', hex:'#49B894', sw:['#F4F0E7','#49B894','#E57A3F'] },
  { id:'clay',   t:'陶土信号', en:'#E57A3F', hex:'#E57A3F', sw:['#FFF8EC','#E57A3F','#173C8F'] },
  { id:'night',  t:'夜蓝花园', en:'#76A5FF', hex:'#76A5FF', sw:['#10253B','#76A5FF','#62C7A5'] },
];
const BLOCKS = [
  { id:'hero', t:'Hero 主视觉' }, { id:'feats', t:'特性网格' }, { id:'pricing', t:'价格表' },
  { id:'faq', t:'FAQ' }, { id:'kpi', t:'KPI 指标' }, { id:'chart', t:'柱状图' },
  { id:'table', t:'数据表格' }, { id:'cover', t:'章节封面' }, { id:'quote', t:'大字口号' },
  { id:'road', t:'路线图' }, { id:'layers', t:'架构分层' }, { id:'cta', t:'CTA 行动栏' },
];
const BLOCK_TEXT = {
  hero:'主标题：把想法变成可交付的成果\n副标题：为高效团队打造的下一代创作工具',
  feats:'特性：Brief 标准 · 审美模板 · 反馈迭代 · 联盟路由',
  pricing:'价格：免费版 ¥0 / 专业版 ¥99每月 / 企业版 联系我们',
  faq:'FAQ：数据安全？可随时取消？有 API 吗？',
  kpi:'指标：总用户 24813 · 月活跃 8392 · 转化 4.6% · 今日收入 ¥18204',
  chart:'图表：周一到周日的访问趋势',
  table:'表格：最近订单与状态',
  cover:'封面标题：重新定义团队的创作方式',
  quote:'口号：经验应该被沉淀，而不是被重复',
  road:'路线图：Q3 开源 · Q4 联盟 · Q1 模板市场',
  layers:'分层：入口层 / 编排层 / 联盟层 / 沉淀层 / 模型层',
  cta:'行动：立即免费开始 →',
};
const LAYOUTS = [
  { intent:'deck', t:'发布会 PPT' },
  { intent:'doc', t:'文档' },
  { intent:'poster', t:'海报 / 一页纸' },
  { intent:'landing', t:'落地页' },
  { intent:'dashboard', t:'数据看板' },
  { intent:'archdoc', t:'架构文档' },
];
const INTENT_LABEL = { landing:'落地页', dashboard:'数据看板', deck:'发布会 PPT', poster:'海报', archdoc:'架构文档', doc:'文档' };
const miniOf = (kind, id) => `<div class="mini">${(kind === 'page' ? PAGE_MINI : MINI)[id] || ''}</div>`;

/* ============================================================ */
const $ = s => document.querySelector(s);
const UI_THEMES = { 'pixel-paper': { label:'夜蓝', color:'#FFFDF6' }, 'pixel-night': { label:'纸白', color:'#16314A' } };
function applyTheme(theme) {
  const next = UI_THEMES[theme] ? theme : 'pixel-paper';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('fox-ui-theme', next); } catch(e) {}
  const label = document.getElementById('theme-label');
  if (label) label.textContent = UI_THEMES[next].label;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = UI_THEMES[next].color;
}
function toggleTheme() {
  applyTheme(document.documentElement.dataset.theme === 'pixel-night' ? 'pixel-paper' : 'pixel-night');
}
/* 文本 → HTML 属性安全文本。单引号一并转义：esc() 的结果不只进入 HTML，
 * 还会被塞进模板里的 JS 字符串（例如 onclick="intakeApprove('${esc(id)}')"），
 * 漏掉单引号会让 id 里的 ' 闭合字符串。
 * 当前 candidate_id 已被服务端正则限制为 [a-z0-9.-]，所以这还不是可利用
 * 的漏洞；但它是个会误导后来者的坏味道，先补上。 */
const esc = s => (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
let camera = { x:0, y:0, z:1 };
let nodes = [], edges = [], selected = null, selectedIds = new Set(), uid = 1, wsSeq = 1, activeWorkspaceId = null;
/* G7 · 组框容器元数据（成员关系仍以 node.groupId 为准，这里只存组名与配色） */
let groups = [], groupSeq = 1;
let workspaceNavigatorCollapsed = false;
/* G1 网格吸附档位（8/16/32/0=关闭），随工作区快照持久化；G3 入场动效只在初始化完成后对新增节点播放 */
const SNAP_LEVELS = window.FoxCanvasEngine?.snapLevels || [8, 16, 32, 0];
let snapLevel = window.FoxCanvasEngine?.defaultGridSize || 16;
let allowNodeEnter = false;
const WORKSPACE_COLORS = [
  { hex:'#5B8DEF', tint:'rgba(91,141,239,.07)' },
  { hex:'#27A87D', tint:'rgba(39,168,125,.07)' },
  { hex:'#E07A3F', tint:'rgba(224,122,63,.07)' },
  { hex:'#C45C8A', tint:'rgba(196,92,138,.07)' },
  { hex:'#8A72D8', tint:'rgba(138,114,216,.07)' },
  { hex:'#B38A2E', tint:'rgba(179,138,46,.07)' },
];
const worldEl = $('#world'), nodesEl = $('#nodes'), edgesEl = $('#edges'), viewport = $('#viewport'), groupsEl = $('#groups');
const guideX = $('#guide-x'), guideY = $('#guide-y');
const state = { templates: [], gallery: [], projects: [], alliance: [], ai: { enabled:false }, memory:null };
const canvasEngine = FoxCanvasEngine.create({ viewport, getCamera:() => camera, getNodes:() => nodes,
  guideX, guideY, getNodeElement:id => document.getElementById('node-' + id) });
let deferredInstallPrompt = null;

function closeMobilePanels() {
  $('#sidebar').classList.remove('mobile-open');
  $('#inspector').classList.remove('mobile-open');
  document.querySelectorAll('[aria-controls="sidebar"],[aria-controls="inspector"]').forEach(button => button.setAttribute('aria-expanded','false'));
  $('#mobile-scrim').classList.remove('on');
}
function toggleMobilePanel(id) {
  const panel = $('#' + id);
  const opening = !panel.classList.contains('mobile-open');
  closeMobilePanels();
  if (opening) {
    panel.classList.add('mobile-open');
    document.querySelector(`[aria-controls="${id}"]`)?.setAttribute('aria-expanded','true');
    $('#mobile-scrim').classList.add('on');
  }
}
applyTheme(document.documentElement.dataset.theme);

function updateConnectionStatus() {
  const status = $('#status');
  if (!navigator.onLine) { status.textContent = '离线：工作区可编辑，生成需连接本地服务'; status.classList.remove('ok'); }
}
window.addEventListener('online', () => { $('#status').textContent = ''; });
window.addEventListener('offline', updateConnectionStatus);
window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault(); deferredInstallPrompt = e; $('#btn-install').hidden = false;
});
window.addEventListener('appinstalled', () => { deferredInstallPrompt = null; $('#btn-install').hidden = true; });
window.addEventListener('pagehide', () => {
  try { fetch('/api/workspace', { method:'PUT', headers:{'Content-Type':'application/json'},
    body:JSON.stringify(workspaceSnapshot()), keepalive:true }); } catch(e) {}
});

let remoteSaveTimer = null, restoringWorkspace = false, remoteSaveFailed = false;
function workspaceSnapshot() {
  return { schema_version:1, saved_at:new Date().toISOString(),
    canvas:{ camera, nodes, edges, groups, uid, wsSeq, activeWorkspaceId, workspaceNavigatorCollapsed, snapLevel } };
}
function normalizeWorkspaceState() {
  const workspaces = nodes.filter(n => n.kind === 'ws');
  workspaces.forEach((ws, index) => {
    ws.data = ws.data || {};
    ws.title = ws.data.title || ws.title || `工作区 ${index + 1}`;
    ws.data.title = ws.title;
    ws.data.color = ws.data.color || WORKSPACE_COLORS[index % WORKSPACE_COLORS.length].hex;
    ws.data.tint = ws.data.tint || workspaceColor(ws.data.color).tint;
  });
  for (const node of nodes.filter(n => n.kind !== 'ws')) {
    if (node.workspaceId && !workspaces.some(ws => ws.id === node.workspaceId)) node.workspaceId = null;
    if (!node.workspaceId) node.workspaceId = workspaceAtNode(node)?.id || null;
  }
  if (!workspaces.some(ws => ws.id === activeWorkspaceId)) activeWorkspaceId = workspaces[0]?.id ?? null;
}
function applyWorkspaceSnapshot(snapshot) {
  const canvas = snapshot && (snapshot.canvas || snapshot);
  if (!canvas || !Array.isArray(canvas.nodes) || !Array.isArray(canvas.edges)) return false;
  restoringWorkspace = true;
  camera = canvas.camera || { x:0, y:0, z:1 }; nodes = canvas.nodes; edges = canvas.edges;
  groups = Array.isArray(canvas.groups) ? canvas.groups : [];
  selected = null; selectedIds.clear();
  uid = canvas.uid || (Math.max(0, ...nodes.map(n => Number(n.id) || 0)) + 1); wsSeq = canvas.wsSeq || 1;
  activeWorkspaceId = canvas.activeWorkspaceId ?? null;
  workspaceNavigatorCollapsed = Boolean(canvas.workspaceNavigatorCollapsed);
  snapLevel = SNAP_LEVELS.includes(canvas.snapLevel) ? canvas.snapLevel : (window.FoxCanvasEngine?.defaultGridSize || 16);
  normalizeWorkspaceState();
  restoringWorkspace = false;
  return true;
}
async function persistWorkspaceNow() {
  clearTimeout(remoteSaveTimer);
  const result = await api('/api/workspace', 'PUT', workspaceSnapshot());
  remoteSaveFailed = false;
  return result;
}
function save() {
  const snapshot = workspaceSnapshot();
  localStorage.setItem('fox-canvas-v3', JSON.stringify(snapshot));
  if (!restoringWorkspace) window.FoxCanvasProductivity?.scheduleHistory();
  if (restoringWorkspace) return;
  clearTimeout(remoteSaveTimer);
  remoteSaveTimer = setTimeout(async () => {
    try { await api('/api/workspace', 'PUT', snapshot); remoteSaveFailed = false; }
    catch (e) {
      if (!remoteSaveFailed) { $('#status').textContent = '云端快照未保存：' + e.message; remoteSaveFailed = true; }
    }
  }, 650);
}
function loadSaved() {
  try { return applyWorkspaceSnapshot(JSON.parse(localStorage.getItem('fox-canvas-v3'))); } catch(e) {}
  return false;
}
async function loadRemoteWorkspace() {
  try {
    const data = await api('/api/workspace');
    if (!data.exists || !applyWorkspaceSnapshot(data.state)) return false;
    localStorage.setItem('fox-canvas-v3', JSON.stringify(data.state));
    flash(data.recovered ? '已从备份恢复工作区' : '已从服务端恢复工作区', true);
    return true;
  } catch(e) { return false; }
}
let cameraAnimTimer = null;
function stopCameraAnimation() {
  clearTimeout(cameraAnimTimer);
  cameraAnimTimer = null;
  worldEl.classList.remove('is-animating');
}
/* G2 相机缓动：animate=true 只用于程序化跳转（适配全部 / 定位节点 / HUD 缩放按钮 / 小地图跳转）。
   拖平移与滚轮平移必须保持 false，否则跟手会飘。 */
function applyCamera(commit = true, animate = false) {
  if (animate && window.FoxMotion?.enabled()) {
    clearTimeout(cameraAnimTimer);
    worldEl.classList.add('is-animating');
    cameraAnimTimer = setTimeout(stopCameraAnimation, 260);
  } else if (worldEl.classList.contains('is-animating')) stopCameraAnimation();
  worldEl.style.transform = `translate3d(${camera.x}px,${camera.y}px,0) scale(${camera.z})`;
  $('#zoom-label').textContent = Math.round(camera.z * 100) + '%';
  document.querySelector('.canvas-wrap')?.setAttribute('data-canvas-density', camera.z < .78 ? 'overview' : camera.z < 1 ? 'compact' : 'detail');
  window.FoxCanvasProductivity?.scheduleMinimap();
  if (commit) save();
}
worldEl.addEventListener('transitionend', event => { if (event.propertyName === 'transform') stopCameraAnimation(); });

/* G1 网格吸附档位：8 / 16 / 32 / 关闭（0 = 只保留对齐线） */
function applySnapLevel(next) {
  snapLevel = SNAP_LEVELS.includes(next) ? next : (window.FoxCanvasEngine?.defaultGridSize || 16);
  const button = document.getElementById('snap-level');
  if (button) {
    button.textContent = snapLevel ? snapLevel : '—';
    button.title = snapLevel ? `网格吸附 ${snapLevel}px（Ctrl+G 循环，Alt 拖动临时关闭）` : '网格吸附已关闭，仅保留对齐线（Ctrl+G 循环）';
  }
  return snapLevel;
}
function cycleSnapLevel() {
  const index = SNAP_LEVELS.indexOf(snapLevel);
  applySnapLevel(SNAP_LEVELS[(index + 1) % SNAP_LEVELS.length]);
  save();
  flash(snapLevel ? `网格吸附 ${snapLevel}px` : '网格吸附已关闭，仅保留对齐线', true);
  return snapLevel;
}
function toWorld(e) { return canvasEngine.screenToWorld(e.clientX, e.clientY); }
let viewportCommitTimer = null;
function scheduleViewportCommit() {
  clearTimeout(viewportCommitTimer); viewportCommitTimer = setTimeout(save, 180);
}
function zoomBy(f, cx, cy, animate = true) {
  const r = viewport.getBoundingClientRect();
  cx = cx ?? r.width / 2; cy = cy ?? r.height / 2;
  const wx = (cx - camera.x) / camera.z, wy = (cy - camera.y) / camera.z;
  camera.z = Math.min(2.4, Math.max(0.25, camera.z * f));
  camera.x = cx - wx * camera.z; camera.y = cy - wy * camera.z;
  applyCamera(false, animate); scheduleViewportCommit();
}
/* 画布上浮动控件的避让区域。
 * 工作区导航卡是**左上角一块浮层**，不是一条通高的左栏。此前按
 * `left: 导航卡右缘` 预留，把 916px 画布的可用宽度压到 446px，缩放被逼到
 * 0.33，内容缩成一小团、右侧空出 666px。现在按各浮层的真实几何分别计入
 * 上 / 下 / 右三边，画布宽度被真正用起来。 */
function canvasFitInsets() {
  const viewportRect = viewport.getBoundingClientRect();
  const empty = { left:0, top:0, right:0, bottom:0 };
  if (viewportRect.width < 720) return empty;
  const inset = (id, edge, gap) => {
    const el = document.getElementById(id);
    if (!el || el.offsetParent === null) return 0;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return 0;
    if (edge === 'top') return Math.max(0, r.bottom - viewportRect.top + gap);
    if (edge === 'bottom') return Math.max(0, viewportRect.bottom - r.top + gap);
    if (edge === 'right') return Math.max(0, viewportRect.right - r.left + gap);
    return Math.max(0, r.right - viewportRect.left + gap);
  };
  return {
    left: 0,
    top: inset('workspace-navigator', 'top', 16),
    right: Math.max(inset('hud', 'right', 12), 0),
    bottom: inset('minimap', 'bottom', 16),
  };
}
function fitRect(x, y, w, h, pad = 36, animate = true) {
  const r = viewport.getBoundingClientRect();
  const insets = canvasFitInsets();
  const safeW = Math.max(1, w), safeH = Math.max(1, h);
  const availableW = Math.max(160, r.width - insets.left - insets.right - pad*2);
  const availableH = Math.max(160, r.height - insets.top - insets.bottom - pad*2);
  const z = Math.max(0.3, Math.min(1.5, Math.min(availableW / safeW, availableH / safeH)));
  camera.z = z;
  camera.x = insets.left + pad + (availableW - safeW * z) / 2 - x * z;
  camera.y = insets.top + pad + (availableH - safeH * z) / 2 - y * z;
  applyCamera(true, animate);
}
function fitAll(animate = true) {
  const vis = nodes.filter(n => n.kind !== 'ws');
  if (!vis.length) { camera = {x:viewport.clientWidth/2,y:viewport.clientHeight/2,z:1}; return applyCamera(true, animate); }
  let x1=1e9,y1=1e9,x2=-1e9,y2=-1e9;
  for (const n of vis) { const size=canvasEngine.nodeSize(n); x1=Math.min(x1,n.x); y1=Math.min(y1,n.y);
    x2=Math.max(x2,n.x+size.width); y2=Math.max(y2,n.y+size.height); }
  fitRect(x1,y1,x2-x1,y2-y1, 90, animate);
}
function resetView() { fitAll(); }
viewport.addEventListener('wheel', e => {
  e.preventDefault();
  if (e.ctrlKey || e.metaKey) { const r=viewport.getBoundingClientRect(); zoomBy(e.deltaY<0?1.1:1/1.1,e.clientX-r.left,e.clientY-r.top,false); }
  else { camera.x-=e.deltaX; camera.y-=e.deltaY; applyCamera(false); scheduleViewportCommit(); }
}, {passive:false});

/* ================= 平移 / 拖拽 / 缩放句柄 ================= */
let pan=null,drag=null,resize=null,linking=null,pointerFrame=null,pendingPointer=null;
/* 节点世界坐标走 CSS 变量：transform 只用来播放入场/落位动效，两者不再互相覆盖（G3 前置净改造） */
function placeNode(n) { const el=document.getElementById('node-'+n.id); if(el){el.style.setProperty('--nx',n.x+'px');el.style.setProperty('--ny',n.y+'px');} window.FoxCanvasProductivity?.scheduleMinimap(); scheduleGroupRender(); }
function nodePorts(n) { return `<div class="port port-in" data-port="${n.id}" data-port-side="in" title="连接输入"></div>
  <div class="port port-out" data-port="${n.id}" data-port-side="out" title="拖动连接 · 放到目标卡片或输入端口即可吸附"></div>`; }
function clearLinkTarget(){document.querySelectorAll('.port.link-target,.node.link-target,.node.smart-target').forEach(el=>el.classList.remove('link-target','smart-target'));}
function setLinkTarget(target){clearLinkTarget();if(!target)return;target.port.classList.add('link-target');const node=target.port.closest('.node');node?.classList.add('link-target');if(target.capture==='node')node?.classList.add('smart-target');}
function beginNodePointer(e,n){
  if(e.target.closest('button'))return;
  const additive=e.shiftKey||e.ctrlKey||e.metaKey;
  if(e.target.dataset.resize){
    e.preventDefault();e.stopPropagation();select(n.id);
    if(n.locked)return flash('节点已锁定，请先解锁',false);
    viewport.setPointerCapture?.(e.pointerId);resize={id:n.id,pointerId:e.pointerId,startW:n.w,startH:n.h};return;
  }
  if(e.target.closest('.port'))return;
  if(e.target.closest('textarea,select,input,iframe')){select(n.id,{additive});return;}
  if(n.locked){select(n.id,{additive});return flash('节点已锁定，请先解锁',false);}
  const canDragWorkspace = n.kind !== 'ws' || e.target === e.currentTarget || e.target.closest('[data-drag]');
  if(!canDragWorkspace){select(n.id,{additive});return;}
  if(additive)select(n.id,{toggle:true});
  else if(n.groupId)selectMany(nodes.filter(item=>item.groupId===n.groupId).map(item=>item.id));
  else if(!selectedIds.has(n.id))select(n.id);
  else select(n.id,{preserve:true});
  if(!selectedIds.has(n.id))return;
  e.preventDefault();viewport.setPointerCapture?.(e.pointerId);const[wx,wy]=toWorld(e);
  const moving=window.FoxCanvasProductivity?.dragMembers(n)||[n];
  drag={id:n.id,pointerId:e.pointerId,ox:wx-n.x,oy:wy-n.y,startX:n.x,startY:n.y,
    snapSession:canvasEngine.createSnapSession(),starts:moving.map(item=>({id:item.id,x:item.x,y:item.y}))};
  moving.forEach(item=>document.getElementById('node-'+item.id)?.classList.add('dragging'));
}
viewport.addEventListener('pointerdown',e=>{if(!e.isPrimary)return;if(e.target===viewport||e.target===worldEl||e.target===nodesEl||e.target.classList.contains('grid-bg')){
  e.preventDefault();viewport.setPointerCapture?.(e.pointerId);
  if(window.FoxCanvasProductivity?.beginLasso(e))return;
  pan={pointerId:e.pointerId,sx:e.clientX,sy:e.clientY,cx:camera.x,cy:camera.y};viewport.classList.add('panning');select(null);}});
document.addEventListener('pointerdown',e=>{const port=e.target.closest?.('.port-out');if(!port)return;e.preventDefault();e.stopPropagation();
  const node=nodes.find(item=>item.id===Number(port.dataset.port));if(node?.locked)return flash('节点已锁定，请先解锁',false);
  viewport.setPointerCapture?.(e.pointerId);linking={from:Number(port.dataset.port),pointerId:e.pointerId,target:null};document.getElementById('node-'+linking.from)?.classList.add('link-source');highlightCandidatePorts(linking.from);const start=canvasEngine.portPoint(linking.from,'out');if(start)tempEdge(start,start);});
function handlePointerMove(e){
  if(window.FoxCanvasProductivity?.moveLasso(e))return;
  if(pan){camera.x=pan.cx+e.clientX-pan.sx;camera.y=pan.cy+e.clientY-pan.sy;applyCamera(false);}
  if(drag){const[wx,wy]=toWorld(e),n=nodes.find(item=>item.id===drag.id);if(n){const snapped=canvasEngine.snapNode(n,wx-drag.ox,wy-drag.oy,{disabled:e.altKey,grid:snapLevel>0,gridSize:snapLevel||undefined,excludeIds:drag.starts.map(item=>item.id),session:drag.snapSession});
    const dx=snapped.x-drag.startX,dy=snapped.y-drag.startY;
    for(const start of drag.starts){const member=nodes.find(item=>item.id===start.id);if(member){member.x=start.x+dx;member.y=start.y+dy;placeNode(member);}}
    canvasEngine.showGuides(snapped);drawEdges();}}
  if(resize){const n=nodes.find(item=>item.id===resize.id);if(n){const[wx,wy]=toWorld(e);n.w=Math.max(360,Math.round((wx-n.x)/16)*16);
    n.h=Math.max(260,Math.round((wy-n.y)/16)*16);const el=document.getElementById('node-'+n.id);if(el){el.style.width=n.w+'px';el.style.height=n.h+'px';}drawEdges();window.FoxCanvasProductivity?.scheduleMinimap();}}
  if(linking){const start=canvasEngine.portPoint(linking.from,'out');if(start){linking.target=canvasEngine.nearestInput(e.clientX,e.clientY,linking.from,linking.target);setLinkTarget(linking.target);
    const end=linking.target?canvasEngine.portPoint(linking.target.nodeId,'in'):(()=>{const p=toWorld(e);return{x:p[0],y:p[1]};})();tempEdge(start,end);}}
}
window.addEventListener('pointermove',e=>{pendingPointer=e;if(pointerFrame)return;pointerFrame=requestAnimationFrame(()=>{pointerFrame=null;const event=pendingPointer;pendingPointer=null;handlePointerMove(event);});});
function finishPointerInteraction(e){let changed=false;
  if(e?.type==='pointerup'&&(pan||drag||resize||linking)){if(pointerFrame){cancelAnimationFrame(pointerFrame);pointerFrame=null;}pendingPointer=null;handlePointerMove(e);}
  if(window.FoxCanvasProductivity?.finishLasso(e)){if(e?.pointerId!=null&&viewport.hasPointerCapture?.(e.pointerId))viewport.releasePointerCapture(e.pointerId);return;}
  if(drag){const primary=nodes.find(item=>item.id===drag.id);if(primary){const settled=canvasEngine.settleNode(primary);const adjustX=settled.x-primary.x,adjustY=settled.y-primary.y;
    for(const start of drag.starts){const member=nodes.find(item=>item.id===start.id);if(member){member.x+=adjustX;member.y+=adjustY;if(member.kind!=='ws')member.workspaceId=workspaceAtNode(member)?.id||null;placeNode(member);
      if(member.x!==start.x||member.y!==start.y)changed=true;}}}
    for(const start of drag.starts)document.getElementById('node-'+start.id)?.classList.remove('dragging');}
  if(resize){const n=nodes.find(item=>item.id===resize.id);if(n&&(n.w!==resize.startW||n.h!==resize.startH))changed=true;}
  if(pan)changed=true;if(linking){if(linking.target&&!edges.some(edge=>edge.from===linking.from&&edge.to===linking.target.nodeId)){
  edges.push({from:linking.from,to:linking.target.nodeId});changed=true;const sourceNode=nodes.find(item=>item.id===linking.from),targetNode=nodes.find(item=>item.id===linking.target.nodeId);flash('已智能连接：'+(sourceNode?.title||'节点')+' → '+(targetNode?.title||'节点'),true);}
  document.getElementById('node-'+linking.from)?.classList.remove('link-source');linking=null;clearLinkTarget();clearCandidatePorts();clearTempEdge();}
  pan=null;drag=null;resize=null;viewport.classList.remove('panning');canvasEngine.clearGuides();drawEdges();updateWsCount();renderWorkspaceNavigator();timeline();if(changed){save();window.FoxCanvasProductivity?.commitHistory();}
  if(e?.pointerId!=null&&viewport.hasPointerCapture?.(e.pointerId))viewport.releasePointerCapture(e.pointerId);}
window.addEventListener('pointerup',finishPointerInteraction);window.addEventListener('pointercancel',finishPointerInteraction);

/* ================= 节点渲染 ================= */
function addNode(kind, x, y, data = {}) {
  if (kind === 'ws') {
    const palette = WORKSPACE_COLORS[(wsSeq - 1) % WORKSPACE_COLORS.length];
    data.color = data.color || palette.hex; data.tint = data.tint || palette.tint;
  }
  const n = { id: uid++, kind, x: Math.round(x), y: Math.round(y),
    w: kind === 'ws' ? 880 : kind === 'output' || kind === 'file' ? 430 : 226,
    h: kind === 'ws' ? 540 : undefined,
    workspaceId: data.workspaceId ?? null,
    title: data.title || '', data };
  if (kind === 'requirement' && !n.data.text) n.data.text = '';
  if (kind === 'block' && !n.data.text) n.data.text = BLOCK_TEXT[data.blockId] || '';
  if (kind === 'template') { n.data.intent = n.data.intent || 'landing'; n.data.template = n.data.template || ''; }
  nodes.push(n); renderNode(n);
  if (kind !== 'ws' && n.workspaceId == null) {
    const settled = canvasEngine.settleNode(n); n.x = settled.x; n.y = settled.y;
    n.workspaceId = settled.workspaceId; placeNode(n);
  }
  if (kind === 'ws') activeWorkspaceId = n.id;
  select(n.id); save(); timeline(); updateWsCount(); renderWorkspaceNavigator();
  return n;
}
function kindLabel(k) { return { requirement:'需求', block:'内容', template:'版式', style:'风格',
  color:'色卡', font:'字体', source:'输入文件', file:'文件', skill:'技能', output:'产物', ws:'工作区', note:'brief' }[k] || k; }

/* G3：入场/落位只播一轮，animationend 摘类，避免动画值长期盖住静态 transform */
function animateNode(el, className, animationName) {
  window.FoxMotion?.animateClass(el, className, animationName);
}
function renderNode(n) {
  const el = document.createElement('div');
  el.className = 'node ' + n.kind + (n.locked ? ' locked' : '') + (n.groupId ? ' grouped' : '') + (selectedIds.has(n.id) ? ' selected' : ''); el.id = 'node-' + n.id;
  el.style.setProperty('--nx', n.x + 'px');
  el.style.setProperty('--ny', n.y + 'px');
  if (n.w) el.style.width = n.w + 'px';
  if (n.h) el.style.height = n.h + 'px';
  el.dataset.id = n.id;
  const head = (icon, g, extra='') => `<div class="node-head" data-drag="${n.id}">
    <span class="pal-ico" style="background:${g};width:20px;height:20px;border-radius:4px;display:inline-flex;align-items:center;justify-content:center;color:#fff;flex:none"><span class="ui-icon" data-icon="${icon}" aria-hidden="true"></span></span>
    <span class="hd-title">${esc(n.title)}</span>${extra}<span class="kind">${kindLabel(n.kind)}</span></div>`;

  if (n.kind === 'ws') {
    applyWorkspaceAppearance(n, el);
    el.innerHTML = `<div class="ws-head" data-drag="${n.id}">
        <span class="workspace-mark" style="color:var(--workspace-color)"><span class="ui-icon" data-icon="workspace" aria-hidden="true"></span></span><span class="nm" ondblclick="event.stopPropagation();quickRenameWorkspace(${n.id})" title="双击重命名">${esc(n.title)}</span>
        <span class="cnt" id="ws-cnt-${n.id}"></span>
        <button onclick="event.stopPropagation();fitWs(${n.id})" title="自动缩放到此工作区"><span class="ui-icon" data-icon="fit" aria-hidden="true"></span>适配</button>
        <button class="go" onclick="event.stopPropagation();advanceWs(${n.id})" id="ws-go-${n.id}"><span class="ui-icon" data-icon="play" aria-hidden="true"></span>推进</button>
      </div><div class="ws-handle" data-resize="${n.id}"></div>`;
  } else if (n.kind === 'requirement') {
    el.innerHTML = head('prompt', 'linear-gradient(135deg,#B45309,#F59E0B)', '<span class="rev-chip" id="an-st-${n.id}" style="display:none"></span>') +
      `<div class="node-body"><textarea data-bind="text" placeholder="输入文字需求，或通过顶部“输入需求”添加文件/图片…">${esc(n.data.text)}</textarea>
       ${(n.data.attachments||[]).length ? `<div class="attachment-chips">${n.data.attachments.map(item=>`<span>${esc(item.name)}</span>`).join('')}</div>` : ''}
       <div class="an-chips" id="an-${n.id}"></div></div>${nodePorts(n)}`;
  } else if (n.kind === 'source') {
    el.innerHTML = head(n.data.kind === 'image' ? 'image' : 'file', 'linear-gradient(135deg,var(--cyan),var(--green))') +
      `<div class="node-body" style="font-size:var(--fs-sm)"><strong>${esc(n.data.name || n.title)}</strong>
       <div style="margin-top:5px;color:var(--text-tertiary)">${esc(n.data.mime || n.data.kind || '附件')} · ${Math.ceil((n.data.size || 0)/1024)}KB</div></div>${nodePorts(n)}`;
  } else if (n.kind === 'block') {
    el.innerHTML = head('content', 'linear-gradient(135deg,var(--accent),var(--green))') +
      (n.data.preview_url ? `<div class="template-node-preview"><iframe src="${esc(n.data.preview_url)}" title="${esc(n.title)} HTML 预览" sandbox="allow-scripts allow-same-origin"></iframe></div>` : `<div class="thumb-mini">${miniOf('block', n.data.blockId)}</div>`) +
      `<div class="node-body" style="padding-top:2px"><textarea data-bind="text" style="min-height:34px;font-size:var(--fs-sm)">${esc(n.data.text)}</textarea></div>
       ${nodePorts(n)}`;
  } else if (n.kind === 'template') {
    el.innerHTML = head('layout', 'linear-gradient(135deg,var(--accent),var(--green))') +
      `<div class="template-node-preview"><iframe data-template-frame title="${esc(n.title)}版式预览" sandbox="allow-scripts allow-same-origin"></iframe></div>
       <div class="node-body" style="padding-top:7px">
       <select data-bind="intent">${LAYOUTS.map(l => `<option value="${l.intent}"${n.data.intent===l.intent?' selected':''}>${l.t}</option>`).join('')}</select>
       <select data-bind="template"><option value="">风格自动</option></select></div>
       ${nodePorts(n)}`;
    fillTemplateSelect(el.querySelector('[data-bind="template"]'), n.data.template);
    el.querySelector('[data-template-frame]').src=n.data.preview_url || previewUrl(n.data.intent,n.data.template);
  } else if (n.kind === 'style') {
    el.innerHTML = head('palette', 'var(--accent)') +
      `<div class="template-node-preview"><iframe data-style-frame title="${esc(n.title)}风格预览" sandbox="allow-scripts allow-same-origin"></iframe></div>
       <div class="node-body" style="padding-top:7px;font-size:var(--fs-sm)">${esc(n.data.title)}</div>
       ${nodePorts(n)}`;
    el.querySelector('[data-style-frame]').src=n.data.preview_url || previewUrl(n.data.intent||'landing',n.data.preset||'');
  } else if (n.kind === 'color') {
    el.innerHTML = head('color', `linear-gradient(135deg,${n.data.hex},#00000055)`) +
      `<div class="thumb-mini"><div class="mini" style="display:flex">${(n.data.sw||[]).map(c=>`<i style="position:static;flex:1;border-radius:0;background:${c}"></i>`).join('')}</div></div>
       <div class="node-body" style="padding-top:0;font-size:var(--fs-sm)">${esc(n.data.title)} <span style="color:var(--text-tertiary)">${esc(n.data.hex)}</span></div>
       ${nodePorts(n)}`;
  } else if (n.kind === 'font') {
    el.innerHTML = head('type', 'linear-gradient(135deg,#1F1F2E,#3A3A48)') +
      `<div class="thumb-mini font-card"><div class="mini"><span class="aa" style="font-family:${esc(n.data.css)}">Aa<small>${esc(n.data.en)}</small></span></div></div>
       <div class="node-body" style="padding-top:0;font-size:var(--fs-sm)">${esc(n.data.t)}</div>
       ${nodePorts(n)}`;
  } else if (n.kind === 'skill') {
    el.innerHTML = head('skill', 'linear-gradient(135deg,#134E4A,#22D3EE)') +
      `<div class="node-body" style="font-size:var(--fs-sm)">${esc(n.data.title)}
       <div style="margin-top:3px;color:${n.data.installed?'var(--success)':'var(--text-tertiary)'}">${n.data.installed?'● 已安装':'○ 未安装 → 本地兜底'}</div></div>
       ${nodePorts(n)}`;
  } else if (n.kind === 'file' || n.kind === 'output') {
    el.innerHTML = head(n.kind === 'output' ? 'output' : 'file', 'linear-gradient(135deg,#065F46,#22D3EE)',
      n.kind === 'output' ? `<span class="rev-chip" id="rev-${n.id}">rev${n.data.revision||0}</span>` : '') +
      `<div class="meta-row" id="meta-${n.id}"></div><iframe id="frame-${n.id}" title="${esc(n.data.project_name || n.title)}产物预览" sandbox="allow-same-origin"></iframe>${nodePorts(n)}`;
  }
  nodesEl.appendChild(el);
  if (allowNodeEnter) animateNode(el, 'node-enter', 'fox-node-enter');
  window.FoxGeneration?.renderBadge(el, n);   /* G5：生成中的节点重渲染后要恢复进度环（经模块 API） */
  scheduleGroupRender();  /* G7：节点重建后容器包围盒要跟上 */
  if (n.kind === 'file' || n.kind === 'output') {
    const f = el.querySelector('iframe');
    if (n.data.preview_url) f.src = n.data.preview_url + '?t=' + Date.now();
    el.querySelector(`#meta-${n.id}`).innerHTML =
      `<span class="meta-chip">类型 <b>${esc(INTENT_LABEL[n.data.intent] || n.data.intent || '—')}</b></span>
       <span class="meta-chip">风格 <b>${esc(n.data.preset_id || '—')}</b></span>
       <span class="meta-chip">${esc(n.data.project_name || '')}</span>`;
  }
  el.addEventListener('pointerdown', e => beginNodePointer(e, n));
  el.addEventListener('input', e => {
    const bind = e.target.dataset.bind;
    if (bind) {
      n.data[bind] = e.target.value;
      if (n.kind === 'requirement' && bind === 'text') delete n.data.analysis;
      if (n.kind === 'template' && bind === 'intent') {
        n.title = LAYOUTS.find(l => l.intent === e.target.value)?.t || n.title;
        el.querySelector('.hd-title').textContent = n.title;
      }
      if(n.kind==='template'&&(bind==='intent'||bind==='template'))el.querySelector('[data-template-frame]').src=previewUrl(n.data.intent,n.data.template);
      save(); timeline();
    }
  });
}
function fillTemplateSelect(sel, val) {
  fetch('/api/templates').then(r => r.json()).then(d => {
    sel.innerHTML = '<option value="">风格自动</option>' + d.items.map(t =>
      `<option value="${t.id}"${t.id === val ? ' selected' : ''}>${esc(t.name)}</option>`).join('');
  });
}
function updateWsCount() {
  for (const ws of nodes.filter(n => n.kind === 'ws')) {
    const el = document.getElementById('ws-cnt-' + ws.id);
    if (el) el.textContent = membersOf(ws).length + ' 素材';
  }
}
function selectMany(ids, options = {}) {
  if (!options.additive) selectedIds.clear();
  ids.filter(id => nodes.some(node => node.id === id)).forEach(id => selectedIds.add(id));
  selected = ids.length ? ids[ids.length - 1] : ([...selectedIds].at(-1) ?? null);
  const node = nodes.find(item => item.id === selected);
  const workspace = node ? workspaceForNode(node) : null;
  if (workspace) activeWorkspaceId = workspace.id;
  window.FoxCanvasProductivity?.updateSelectionUI();
  renderInspector(); renderWorkspaceNavigator(); timeline();
}
function select(id, options = {}) {
  if (id == null) { selectedIds.clear(); selected = null; }
  else if (options.toggle) {
    if (selectedIds.has(id)) selectedIds.delete(id); else selectedIds.add(id);
    selected = selectedIds.has(id) ? id : ([...selectedIds].at(-1) ?? null);
  } else if (options.additive) { selectedIds.add(id); selected = id; }
  else if (options.preserve && selectedIds.has(id)) selected = id;
  else { selectedIds.clear(); selectedIds.add(id); selected = id; }
  const node = nodes.find(item => item.id === selected);
  const workspace = node ? workspaceForNode(node) : null;
  if (workspace) activeWorkspaceId = workspace.id;
  window.FoxCanvasProductivity?.updateSelectionUI();
  renderInspector(); renderWorkspaceNavigator(); timeline();
}
document.addEventListener('keydown', e => {
  if (e.key === 'Delete' && selectedIds.size && !e.target.closest('textarea,input,select')) window.FoxCanvasProductivity?.deleteSelection();
  if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'g') { e.preventDefault(); cycleSnapLevel(); }
});

/* ================= 连线（G4 · 增量渲染 + 动效） ================= */
const SVG_NS = 'http://www.w3.org/2000/svg';
const edgeEls = new Map();        /* 'from->to' -> path，差量更新的地基 */
let tempEdgeEl = null;            /* 预览线：常驻单条 path，只改 d */
function edgeKeyOf(edge){return edge.from+'->'+edge.to;}
function edgeClassOf(target){return 'edge'+(target.kind==='output'?' hot':'');}
function edgePath(a,b){const start=canvasEngine.portPoint(a.id,'out'),end=canvasEngine.portPoint(b.id,'in');return start&&end?canvasEngine.edgePath(start,end):'';}
/* 差量：只创建新边、只改变化的 d / class、只淡出消失的边 —— 动画因此不会被下一次重建抹掉 */
function drawEdges(){
  if(edgesEl.getAttribute('width')!=='16000'){edgesEl.setAttribute('width',16000);edgesEl.setAttribute('height',9000);}
  const alive=new Set();
  for(const edge of edges){
    const a=nodes.find(n=>n.id===edge.from),b=nodes.find(n=>n.id===edge.to);
    if(!a||!b)continue;
    const key=edgeKeyOf(edge);alive.add(key);
    let path=edgeEls.get(key);
    const className=edgeClassOf(b);
    if(!path){
      path=document.createElementNS(SVG_NS,'path');
      path.setAttribute('pathLength','1');   /* 归一化路径长度，纯 CSS 就能画生长动画 */
      path.setAttribute('class',className);
      path.dataset.edge=key;
      edgesEl.appendChild(path);
      edgeEls.set(key,path);
      if(allowNodeEnter)playEdgeEnter(path); /* 首屏恢复不播，只有真正新建的边才生长 */
    }else if(path.getAttribute('class')!==className)path.setAttribute('class',className);
    const d=edgePath(a,b);
    if(d&&path.getAttribute('d')!==d)path.setAttribute('d',d);
  }
  for(const [key,path] of [...edgeEls]){
    if(alive.has(key))continue;
    edgeEls.delete(key);
    releaseEdge(path);
  }
  scheduleGroupRender();
}
function playEdgeEnter(path){
  path.classList.add('edge-enter');
  path.addEventListener('animationend',event=>{
    if(event.target===path&&event.animationName==='fox-wire-enter')path.classList.remove('edge-enter');
  },{once:true});
}
function releaseEdge(path){
  path.classList.add('edge-leave');
  let done=false;
  const drop=()=>{if(done)return;done=true;path.remove();};
  path.addEventListener('animationend',event=>{if(event.animationName==='fox-wire-leave')drop();},{once:true});
  setTimeout(drop,320);  /* 兜底：prefers-reduced-motion 下没有动画事件 */
}
function tempEdge(start,end){
  if(!tempEdgeEl||!tempEdgeEl.isConnected){
    tempEdgeEl=document.createElementNS(SVG_NS,'path');
    tempEdgeEl.setAttribute('class','temp');
    edgesEl.appendChild(tempEdgeEl);
  }
  tempEdgeEl.setAttribute('d',canvasEngine.edgePath(start,end));
}
function clearTempEdge(){if(tempEdgeEl){tempEdgeEl.remove();tempEdgeEl=null;}}
/* 候选端口预判：hover / 拖线中的输出端口 → 高亮所有可连接的输入端口 */
function highlightCandidatePorts(fromId){
  clearCandidatePorts();
  document.querySelectorAll('.port-in[data-port]').forEach(port=>{
    if(Number(port.dataset.port)!==Number(fromId))port.classList.add('port-candidate');
  });
}
function clearCandidatePorts(){document.querySelectorAll('.port-candidate').forEach(el=>el.classList.remove('port-candidate'));}
viewport.addEventListener('pointerover',event=>{const port=event.target.closest?.('.port-out');if(port)highlightCandidatePorts(port.dataset.port);});
viewport.addEventListener('pointerout',event=>{const port=event.target.closest?.('.port-out');if(port&&!linking)clearCandidatePorts();});

/* ================= G7 · 组框容器 ================= */
/* 成员关系仍由 node.groupId 定义，容器是从 nodes 派生的可视层；groups 只存组名与配色。 */
const GROUP_PADDING = 20, GROUP_HEADER = 32;
let groupRenderFrame = null;
function groupRecord(groupId){
  let record=groups.find(item=>item.id===groupId);
  if(!record){
    record={id:groupId,title:`组 ${groupSeq++}`,color:WORKSPACE_COLORS[groups.length%WORKSPACE_COLORS.length].hex};
    groups.push(record);
  }else if(!record.color)record.color=WORKSPACE_COLORS[groups.length%WORKSPACE_COLORS.length].hex;
  return record;
}
function groupMembersOf(groupId){return nodes.filter(node=>node.groupId===groupId&&node.kind!=='ws');}
function groupBounds(groupId){
  const members=groupMembersOf(groupId);
  if(!members.length)return null;
  let x1=Infinity,y1=Infinity,x2=-Infinity,y2=-Infinity;
  for(const node of members){
    const size=canvasEngine.nodeSize(node);
    x1=Math.min(x1,node.x);y1=Math.min(y1,node.y);
    x2=Math.max(x2,node.x+size.width);y2=Math.max(y2,node.y+size.height);
  }
  return {x:x1-GROUP_PADDING,y:y1-GROUP_HEADER,width:(x2-x1)+GROUP_PADDING*2,height:(y2-y1)+GROUP_HEADER+GROUP_PADDING};
}
function pruneGroups(){
  const alive=new Set(nodes.map(node=>node.groupId).filter(Boolean));
  groups=groups.filter(record=>alive.has(record.id));
  alive.forEach(id=>groupRecord(id));
  return groups;
}
function scheduleGroupRender(){if(groupRenderFrame)return;groupRenderFrame=requestAnimationFrame(renderGroups);}
function renderGroups(){
  groupRenderFrame=null;
  if(!groupsEl)return;
  const alive=new Set();
  for(const record of pruneGroups()){
    const members=groupMembersOf(record.id);
    const bounds=groupBounds(record.id);
    if(!bounds||!members.length)continue;
    alive.add(record.id);
    let el=groupsEl.querySelector(`[data-group="${record.id}"]`);
    if(!el){
      el=document.createElement('div');
      el.className='group-box';
      el.dataset.group=record.id;
      el.addEventListener('pointerdown',event=>beginGroupPointer(event,record.id));
      groupsEl.appendChild(el);
    }
    el.style.setProperty('--group-color',record.color||'var(--accent)');
    el.style.setProperty('--gx',bounds.x+'px');
    el.style.setProperty('--gy',bounds.y+'px');
    el.style.setProperty('--gw',bounds.width+'px');
    el.style.setProperty('--gh',bounds.height+'px');
    el.classList.toggle('selected',members.every(node=>selectedIds.has(node.id)));
    const signature=record.title+'\u0000'+members.length;
    if(el.dataset.signature!==signature){
      el.dataset.signature=signature;
      el.innerHTML=`<span class="group-label" title="拖动整组移动 · 双击重命名"><i><span class="ui-icon" data-icon="group" aria-hidden="true"></span></i>${esc(record.title)}<b>${members.length}</b></span>`;
    }
  }
  groupsEl.querySelectorAll('.group-box').forEach(el=>{if(!alive.has(el.dataset.group))el.remove();});
}
let lastGroupPress = { id:null, at:0 };
function beginGroupPointer(event,groupId){
  if(event.button!=null&&event.button!==0)return;
  const members=groupMembersOf(groupId).filter(node=>!node.locked);
  if(!members.length)return;
  /* 指针捕获会把 dblclick 重定向到 viewport，所以双击判定放在 pointerdown 里自己算 */
  const onLabel=Boolean(event.target.closest?.('.group-label'));
  const now=Date.now();
  if(onLabel&&lastGroupPress.id===groupId&&now-lastGroupPress.at<450){
    lastGroupPress={id:null,at:0};
    event.preventDefault();event.stopPropagation();
    renameGroup(groupId);
    return;
  }
  lastGroupPress={id:onLabel?groupId:null,at:now};
  /* 修饰键 / 框选模式：不劫持拖动，交给框选（与在空白处拖一致） */
  if(event.shiftKey||event.ctrlKey||event.metaKey||window.FoxCanvasProductivity?.isSelectionMode()){
    event.stopPropagation();
    viewport.setPointerCapture?.(event.pointerId);
    window.FoxCanvasProductivity?.beginLasso(event);
    return;
  }
  event.preventDefault();event.stopPropagation();
  selectMany(members.map(node=>node.id));
  scheduleGroupRender();
  viewport.setPointerCapture?.(event.pointerId);
  const [wx,wy]=toWorld(event);
  const primary=members[0];
  drag={id:primary.id,groupId,pointerId:event.pointerId,ox:wx-primary.x,oy:wy-primary.y,
    startX:primary.x,startY:primary.y,snapSession:canvasEngine.createSnapSession(),
    starts:members.map(node=>({id:node.id,x:node.x,y:node.y}))};
  members.forEach(node=>document.getElementById('node-'+node.id)?.classList.add('dragging'));
}
function renameGroup(groupId){
  const record=groups.find(item=>item.id===groupId);
  if(!record)return;
  const name=prompt('组名称',record.title);
  if(name==null)return;
  record.title=String(name).trim()||record.title;
  groupsEl?.querySelector(`[data-group="${groupId}"]`)?.removeAttribute('data-signature');
  renderGroups();save();window.FoxCanvasProductivity?.scheduleHistory(true);
}
window.FoxCanvasGroups={render:renderGroups,schedule:scheduleGroupRender,
  sync:()=>{pruneGroups();renderGroups();},members:groupMembersOf,bounds:groupBounds,
  rename:renameGroup,list:()=>groups};

/* ================= 工作区 ================= */
function workspaceColor(hex) {
  const known = WORKSPACE_COLORS.find(item => item.hex.toLowerCase() === String(hex || '').toLowerCase());
  if (known) return known;
  const clean = String(hex || '#5B8DEF').replace('#','');
  const value = clean.length === 3 ? clean.split('').map(char => char + char).join('') : clean.padEnd(6,'0').slice(0,6);
  const red = parseInt(value.slice(0,2),16), green = parseInt(value.slice(2,4),16), blue = parseInt(value.slice(4,6),16);
  return { hex:'#' + value, tint:`rgba(${red},${green},${blue},.07)` };
}
function applyWorkspaceAppearance(ws, element = document.getElementById('node-' + ws.id)) {
  if (!element) return;
  const color = workspaceColor(ws.data?.color);
  element.style.setProperty('--workspace-color', color.hex);
  element.style.setProperty('--workspace-tint', ws.data?.tint || color.tint);
}
function workspaceAtNode(node) {
  const width = Number(node.w) || (node.kind === 'output' || node.kind === 'file' ? 430 : 226);
  const height = Number(node.h) || 120;
  const centerX = node.x + width / 2, centerY = node.y + Math.min(height / 2, 72);
  return nodes.find(candidate => candidate.kind === 'ws' && candidate.id !== node.id &&
    centerX >= candidate.x && centerX <= candidate.x + candidate.w &&
    centerY >= candidate.y && centerY <= candidate.y + candidate.h) || null;
}
function workspaceForNode(node) {
  if (!node) return null;
  if (node.kind === 'ws') return node;
  return nodes.find(ws => ws.kind === 'ws' && ws.id === node.workspaceId) || workspaceAtNode(node);
}
function activeWorkspace() {
  return nodes.find(ws => ws.kind === 'ws' && ws.id === activeWorkspaceId) || nodes.find(ws => ws.kind === 'ws') || null;
}
function addWorkspace() {
  const [wx, wy] = toWorld({ clientX: viewport.getBoundingClientRect().left + 330,
                             clientY: viewport.getBoundingClientRect().top + 210 });
  const ws = addNode('ws', wx - 100, wy - 60, { title: `工作区 ${wsSeq}` });
  wsSeq++;
  activeWorkspaceId = ws.id; renderWorkspaceNavigator(); timeline(); fitWs(ws.id);
  return ws;
}
function fitWs(id) {
  const ws = nodes.find(n => n.id === id && n.kind === 'ws');
  if (ws) { activeWorkspaceId = ws.id; select(ws.id); fitRect(ws.x, ws.y, ws.w, ws.h); }
}
function focusWorkspace(id) { fitWs(id); }
function editWorkspace(id) { activeWorkspaceId = id; select(id); }
function quickRenameWorkspace(id) {
  const ws = nodes.find(n => n.id === id && n.kind === 'ws'); if (!ws) return;
  const name = prompt('工作区名称', ws.title); if (name == null) return;
  updateWorkspaceTitle(ws, name);
}
function updateWorkspaceTitle(ws, value) {
  const title = String(value || '').trim() || '未命名工作区';
  ws.title = title; ws.data.title = title;
  const label = document.querySelector(`#node-${ws.id} .ws-head .nm`); if (label) label.textContent = title;
  renderWorkspaceNavigator(); timeline(); save();
}
function setWorkspaceColor(id, hex) {
  const ws = nodes.find(n => n.id === id && n.kind === 'ws'); if (!ws) return;
  const color = workspaceColor(hex); ws.data.color = color.hex; ws.data.tint = color.tint;
  applyWorkspaceAppearance(ws); renderWorkspaceNavigator(); renderInspector(); save();
}
function toggleWorkspaceNavigator() {
  workspaceNavigatorCollapsed = !workspaceNavigatorCollapsed;
  renderWorkspaceNavigator(); save();
}
function renderWorkspaceNavigator() {
  const box = document.getElementById('workspace-navigator'), list = document.getElementById('workspace-list');
  if (!box || !list) return;
  const workspaces = nodes.filter(node => node.kind === 'ws');
  box.classList.toggle('collapsed', workspaceNavigatorCollapsed);
  document.getElementById('workspace-nav-toggle').textContent = workspaceNavigatorCollapsed ? '⌄' : '⌃';
  document.getElementById('workspace-nav-total').textContent = workspaces.length;
  if (!workspaces.length) { list.innerHTML = '<div class="workspace-nav-empty">暂无工作区<br>点击右上角 ＋ 新建</div>'; return; }
  list.innerHTML = workspaces.map(ws => {
    const color = workspaceColor(ws.data?.color);
    return `<div class="workspace-nav-item ${ws.id===activeWorkspaceId?'active':''}">
      <button class="workspace-nav-main" onclick="focusWorkspace(${ws.id})" ondblclick="quickRenameWorkspace(${ws.id})" style="--workspace-color:${color.hex}">
        <span class="workspace-dot"></span><span class="workspace-nav-name">${esc(ws.title)}</span>
        <span class="workspace-nav-count">${membersOf(ws).length}</span></button>
      <button class="workspace-nav-edit" onpointerdown="event.stopPropagation();editWorkspace(${ws.id})" onclick="event.stopPropagation();editWorkspace(${ws.id})" title="编辑工作区">•••</button></div>`;
  }).join('');
}
function membersOf(ws, options = {}) {
  const includeOutputs = Boolean(options.includeOutputs);
  return nodes.filter(node => {
    if (node.kind === 'ws' || node.kind === 'file') return false;
    if (!includeOutputs && node.kind === 'output') return false;
    if (node.workspaceId === ws.id) return true;
    return !node.workspaceId && workspaceAtNode(node)?.id === ws.id;
  });
}

/* ================= 动作派发表（全局名的唯一来源） =================
 *
 * HTML 与模板字符串里的动作名（onclick / onpointerdown）只能取这里的 key。
 * 这块此前是 44 个手写的 `function foo(){ return window.FoxBar.foo(); }`
 * 转发函数，HTML 里的动作字符串与那份清单之间没有任何约束——
 * 引用一个漏登记的名字只会在用户点击时抛 ReferenceError，单元测试与 CI
 * 全绿也发现不了。S20 期间的 `intakeFetchBatch` 死按钮就是这个形状。
 *
 * 现在动作名集中在这里，且 tests/test_action_registry.py 会在测试期静态
 * 校验：任何被 HTML/JS 引用但没有登记的名字，门禁立刻失败。
 *
 * 内部状态与实现仍都在 lifecycle-*.js；画布与各生命周期域只通过
 * window.Fox* API 协作。 */
window.FoxActions = {
  loadProjects: () => window.FoxProjects.load(),
  openOutput: id => window.FoxProjects.open(id),
  renameProject: id => window.FoxProjects.rename(id),
  duplicateProject: id => window.FoxProjects.duplicate(id),
  deleteProject: id => window.FoxProjects.trash(id),
  updateProjectNodes: (oldName, project) => window.FoxProjects.updateNodes(oldName, project),
  advanceActive: () => window.FoxGeneration.advanceActive(),
  advanceWs: (wsId, options) => window.FoxGeneration.advance(wsId, options),
  rerunRecipeStage: (nodeId, stage) => window.FoxGeneration.rerun(nodeId, stage),
  markNodeGenerating: (nodeId, pct) => window.FoxGeneration.mark(nodeId, pct),
  createJobProgressReporter: label => window.FoxGeneration.progressReporter(label),
  finishNodeGenerating: (nodeId, failed) => window.FoxGeneration.finish(nodeId, failed),
  cancelGeneration: () => window.FoxGeneration.cancelActive(),
  openRevisionDiff: nodeId => window.FoxRevisions.open(nodeId),
  closeRevisionDiff: () => window.FoxRevisions.close(),
  loadRevisionDiff: initial => window.FoxRevisions.load(initial),
  selectRevision: revision => window.FoxRevisions.select(revision),
  updateRevisionSelection: () => window.FoxRevisions.updateSelection(),
  saveRevisionLabel: () => window.FoxRevisions.saveLabel(),
  restoreSelectedRevision: () => window.FoxRevisions.restore(),
  sendFeedback: n => window.FoxRevisions.sendFeedback(n),
  openExportCenter: nodeId => window.FoxExports.open(nodeId),
  closeExportCenter: () => window.FoxExports.close(),
  syncExportOptions: () => window.FoxExports.syncOptions(),
  startExport: () => window.FoxExports.start(),
  createDiagnostic: () => window.FoxExports.diagnostic(),
  openIntake: () => window.FoxIntake.open(),
  closeIntake: () => window.FoxIntake.close(),
  intakeRefresh: filter => window.FoxIntake.refresh(filter),
  intakeFetch: () => window.FoxIntake.fetchCandidate(),
  intakeFetchBatch: () => window.FoxIntake.fetchBatch(),
  intakeApprove: id => window.FoxIntake.approve(id),
  intakeReject: id => window.FoxIntake.reject(id),
  intakeTogglePreview: id => window.FoxIntake.togglePreview(id),
  intakeSelectAll: () => window.FoxIntake.selectAllPending(),
  intakeBatch: action => window.FoxIntake.batchApply(action),
  intakeSourceFilter: source => window.FoxIntake.refresh(source || 'pending', source),
  intakeMakeStylePreset: id => window.FoxIntake.makeStylePreset(id),
  openSlideEditor: id => window.FoxSlides.open(id),
  closeSlideEditor: () => window.FoxSlides.close(),
  saveSlideEditor: () => window.FoxSlides.save(),
  intakeImportComponents: id => window.FoxIntake.importComponents(id),
  intakeImportMotion: id => window.FoxIntake.importMotion(id),
  intakeAnalyze: id => window.FoxIntake.analyze(id),
  intakeLoadStats: () => window.FoxIntake.loadStats(),
  openZipPicker: () => document.querySelector('#intake-zip-file').click(),
  openClassic: () => window.open('/classic', '_blank'),
};
/* onclick 字符串靠全局名解析，这里把派发表挂上去。
 * 已存在的同名全局不覆盖——真正��工作台函数优先。 */
for (const [name, fn] of Object.entries(window.FoxActions)) {
  if (!(name in window)) window[name] = fn;
}
document.addEventListener('change', event => {
  if (event.target?.id === 'intake-zip-file' && event.target.files?.[0]) {
    window.FoxIntake.importZip(event.target.files[0]);
    event.target.value = '';
  }
  if (event.target?.classList?.contains('intake-check')) {
    window.FoxIntake.toggleSelect(event.target.dataset.id, event.target.checked);
  }
});

/* 画布孤儿节点清理：经生成模块 API 清进度态，不读模块内部变量。 */
new MutationObserver(() => {
  const gen = window.FoxGeneration;
  if (!gen) return;
  for (const id of new Set([...gen.generatingNodes.keys(), ...gen.generationCleanups.keys()])) {
    if (!nodes.some(node => node.id === id)) { gen.cancelCleanup(id); gen.generatingNodes.delete(id); }
  }
}).observe(nodesEl, {childList:true});
function apiErrorMessage(data, status) {
  if (typeof data?.error === 'string') return data.error;
  return data?.error?.message || data?.message || ('请求失败（HTTP ' + status + '）');
}
async function api(url, method='GET', data=null) {
  const options = { method, headers:{} };
  if (data !== null) { options.headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(data); }
  const response = await fetch(url, options);
  let result = {};
  try { result = await response.json(); } catch(e) {}
  if (!response.ok || result.ok === false) {
    const requestId = result.request_id ? ' · ' + result.request_id : '';
    const error = new Error(apiErrorMessage(result, response.status) + requestId);
    error.status = response.status;
    error.code = result?.error?.code || '';
    error.payload = result;
    throw error;
  }
  return result;
}
const post = (url, data) => api(url, 'POST', data);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
function exportBytes(bytes) {
  const value = Number(bytes || 0);
  if (value >= 1024 * 1024) return (value / 1024 / 1024).toFixed(1) + ' MB';
  if (value >= 1024) return Math.ceil(value / 1024) + ' KB';
  return value + ' B';
}
function flash(msg, ok, type = '') {
  const el = $('#tl-status');
  el.textContent = msg;
  el.className = 'tl-status' + (ok ? ' ok' : '');
  const inferred = type || (ok ? (/正在|任务 .+%|处理中|上传/.test(msg) ? 'info' : 'success') : 'error');
  window.FoxInteraction?.notify(msg, inferred);
}

/* ================= 检查器 ================= */
function recipeStageSummary(stage) {
  const output = stage?.output_summary || {};
  const values = [];
  if (output.intent) values.push(INTENT_LABEL[output.intent] || output.intent);
  if (output.preset_id) values.push(output.preset_id);
  if (output.generator) values.push(output.generator);
  if (output.score !== undefined) values.push('质量 ' + output.score + ' 分');
  if (output.html_bytes) values.push(Math.ceil(output.html_bytes / 1024) + ' KB');
  if (stage?.model) values.push(stage.model);
  if (stage?.fallback_used === true) values.push('已兜底');
  if (stage?.error?.message) values.push(stage.error.message);
  return values.join(' · ') || (stage?.status === 'reused' ? '复用上次结果' : '等待执行');
}
function recipeRunMarkup(run, nodeId=null) {
  if (!run?.stages?.length) return '<p class="ins-empty">本产物暂无 Recipe Run 记录。</p>';
  const statusLabel = {running:'运行中',succeeded:'已完成',failed:'失败'}[run.status] || run.status;
  const duration = run.duration_ms === null || run.duration_ms === undefined ? '—' : run.duration_ms + ' ms';
  return `<div class="recipe-run" id="recipe-run-live">
    <div class="recipe-run-head"><strong>Recipe Run · ${esc(statusLabel)}</strong><span>${duration}</span></div>
    ${run.stages.map((stage, index) => `<div class="recipe-stage ${esc(stage.status)}">
      <div class="recipe-stage-dot">${stage.status === 'succeeded' || stage.status === 'reused' ? '✓' : stage.status === 'failed' ? '!' : index + 1}</div>
      <div><div class="recipe-stage-title">${esc(stage.label || stage.label_en || stage.id)}</div>
      <div class="recipe-stage-meta">${esc(recipeStageSummary(stage))}${stage.duration_ms !== null && stage.duration_ms !== undefined ? ' · ' + stage.duration_ms + ' ms' : ''}</div></div>
      ${nodeId && stage.rerunnable && ['succeeded','failed','reused'].includes(stage.status) ? `<button class="btn btn-secondary" onclick="rerunRecipeStage(${nodeId},'${stage.id}')">重跑</button>` : ''}
    </div>`).join('')}
  </div>`;
}
function updateRecipeRunView(run) {
  const current = document.querySelector('#recipe-run-live');
  if (!current) return;
  const wrapper = document.createElement('div');
  wrapper.innerHTML = recipeRunMarkup(run, selected);
  current.replaceWith(wrapper.firstElementChild);
}
function renderInspector() {
  const box = $('#inspector');
  if (window.FoxCanvasProductivity?.renderSelectionInspector(box)) return;
  const n = nodes.find(x => x.id === selected);
  if (!n) { box.innerHTML = `<h3>检查器</h3><p class="ins-empty">选中节点查看属性。<br><br>
    · <b>工作区</b>：拖素材进来 = 你的模板，点 ▶ 推进<br>
    · <b>需求节点</b>：自动拆解为 类型+风格+要点<br>
    · <b>产物节点</b>：预览 + 口语反馈迭代（rev）</p>`; return; }
  if (n.kind === 'output') {
    box.innerHTML = `<h3>产物</h3>
      <div class="field"><div class="kv"><span>项目</span><span>${esc(n.data.project_name || '')}</span></div>
      <div class="kv"><span>类型</span><span>${esc(INTENT_LABEL[n.data.intent] || '—')}</span></div>
      <div class="kv"><span>风格</span><span>${esc(n.data.preset_id || '—')}</span></div>
      <div class="kv"><span>版本</span><span id="ins-rev">rev${n.data.revision || 0}</span></div></div>
      ${n.data.intent === 'deck' ? `<button class="btn btn-secondary" style="margin-top:8px;width:100%" onclick="openSlideEditor(${n.id})">✏️ 编辑幻灯片</button>` : ''}
      <button class="btn btn-secondary" id="btn-revision-diff" onclick="openRevisionDiff(${n.id})">查看版本差异</button>
      <h3 style="margin-top:14px">运行轨迹</h3>${recipeRunMarkup(n.data.recipe_run, n.id)}
      ${memorySummaryMarkup(n.data.memory_applied)}
      <button class="btn ${isProjectAdopted(n.data.project_name)?'btn-secondary':'btn-primary'}" style="margin-top:9px;width:100%" onclick="adoptProject(${n.id})" ${isProjectAdopted(n.data.project_name)?'disabled':''}>${isProjectAdopted(n.data.project_name)?'✓ 已采用并学习':'♡ 采用此版本并学习'}</button>
      <div class="field"><label>反馈迭代（口语化）</label>
      <textarea id="fb-note" placeholder="颜色深一点，标题大一点，参考 vercel"></textarea></div>
      <button class="btn btn-primary" id="fb-send">⚡ 提交反馈（改 token 重渲染）</button>
      <div class="field" style="margin-top:9px;display:grid;grid-template-columns:1fr 1fr;gap:7px"><button class="btn btn-secondary" onclick="openOutput(${n.id})">↗ 新窗口打开</button><button class="btn btn-primary" onclick="openExportCenter(${n.id})">⇩ 导出 PDF / PNG</button></div>
      <div class="field" style="display:grid;grid-template-columns:1fr 1fr;gap:7px">
        <button class="btn btn-secondary" onclick="renameProject(${n.id})">重命名</button>
        <button class="btn btn-secondary" onclick="duplicateProject(${n.id})">创建副本</button>
      </div>
      <button class="btn btn-danger-ghost" onclick="deleteProject(${n.id})">移入回收站</button>
      <h3 style="margin-top:16px">迭代历史</h3><div id="fb-history">${
        (n.data.feedback || []).map(f => `<div class="fb-item"><span class="rev">rev${f.rev}</span>${esc(f.note)}
        <div class="sug">${esc(f.sug || '')}</div></div>`).join('') || '<p class="ins-empty">反馈后记录在这里。</p>'}</div>`;
    box.querySelector('#fb-send').onclick = () => sendFeedback(n);
  } else if (n.kind === 'file') {
    box.innerHTML = `<h3>历史项目</h3>
      <div class="field"><div class="kv"><span>项目</span><span>${esc(n.data.project_name || '')}</span></div>
      <div class="kv"><span>类型</span><span>${esc(INTENT_LABEL[n.data.intent] || '—')}</span></div>
      <div class="kv"><span>风格</span><span>${esc(n.data.preset_id || '—')}</span></div></div>
      <div class="field" style="display:grid;grid-template-columns:1fr 1fr;gap:7px"><button class="btn btn-primary" onclick="openOutput(${n.id})">↗ 打开产物</button><button class="btn btn-secondary" onclick="openExportCenter(${n.id})">⇩ 导出</button></div>
      ${n.data.intent === 'deck' ? `<button class="btn btn-secondary" style="margin-top:8px;width:100%" onclick="openSlideEditor(${n.id})">✏️ 编辑幻灯片</button>` : ''}
      <button class="btn btn-secondary" id="btn-revision-diff" onclick="openRevisionDiff(${n.id})">查看版本差异</button>
      <div class="field" style="display:grid;grid-template-columns:1fr 1fr;gap:var(--space-2);margin-top:9px">
        <button class="btn btn-secondary" onclick="renameProject(${n.id})">重命名</button>
        <button class="btn btn-secondary" onclick="duplicateProject(${n.id})">创建副本</button>
      </div>
      <button class="btn btn-danger-ghost" onclick="deleteProject(${n.id})">移入回收站</button>`;
  } else if (n.kind === 'requirement') {
    box.innerHTML = `<h3>需求节点</h3>
      <div class="field"><label>文字需求（推进时自动拆解）</label><textarea id="ins-text">${esc(n.data.text)}</textarea></div>
      ${(n.data.attachments||[]).length ? `<div class="field"><label>输入附件</label><div class="attachment-chips">${n.data.attachments.map(item=>`<span>${esc(item.name)}</span>`).join('')}</div></div>` : ''}
      <button class="btn btn-secondary" onclick="openCreatePanel(${n.id})">编辑文字、文件与图片</button>
      <button class="btn btn-primary" style="margin-top:8px" onclick="advanceWs(${workspaceForNode(n)?.id ?? 'null'})">▶ 在所属工作区推进</button>
      <button class="btn btn-danger-ghost" style="margin-top:8px" onclick="delNode(${n.id})">删除节点</button>`;
    box.querySelector('#ins-text').oninput = e => {
      n.data.text = e.target.value;
      delete n.data.analysis;
      const t = document.querySelector(`#node-${n.id} textarea[data-bind="text"]`);
      if (t && document.activeElement !== t) t.value = n.data.text;
      save();
    };
  } else if (n.kind === 'ws') {
    box.innerHTML = `<h3>工作区设置</h3>
      <div class="field"><label>工作区名称</label><input type="text" id="workspace-name" value="${esc(n.title)}" maxlength="48"></div>
      <div class="field"><label>识别颜色</label><div class="workspace-colors">${WORKSPACE_COLORS.map(color =>
        `<button class="workspace-color ${String(n.data.color).toLowerCase()===color.hex.toLowerCase()?'on':''}" style="--swatch:${color.hex}" onclick="setWorkspaceColor(${n.id},'${color.hex}')" title="${color.hex}"></button>`).join('')}</div></div>
      <div class="kv"><span>配方素材</span><span>${membersOf(n).length}</span></div>
      <div class="kv"><span>生成产物</span><span>${membersOf(n,{includeOutputs:true}).filter(item=>item.kind==='output').length}</span></div>
      <div class="kv"><span>尺寸</span><span>${n.w} × ${n.h}</span></div>
      <p class="ins-empty" style="margin-top:10px">可拖动工作区任意空白区域整体移动；内部素材会保持相对位置。双击画布标题或列表名称也可快速重命名。</p>
      <div class="field" style="display:grid;grid-template-columns:1fr 1fr;gap:var(--space-2);margin-top:10px">
        <button class="btn btn-secondary" onclick="fitWs(${n.id})">⤢ 定位</button>
        <button class="btn btn-primary" onclick="advanceWs(${n.id})">▶ 推进</button>
      </div>
      <button class="btn btn-danger-ghost" style="margin-top:8px" onclick="delNode(${n.id})">删除工作区（保留素材）</button>`;
    box.querySelector('#workspace-name').oninput = event => updateWorkspaceTitle(n, event.target.value);
  } else {
    box.innerHTML = `<h3>${kindLabel(n.kind)}素材</h3>
      <div class="kv"><span>名称</span><span>${esc(n.data.title || n.title)}</span></div>
      ${n.data.preset ? `<div class="kv"><span>预设</span><span>${esc(n.data.preset)}</span></div>` : ''}
      ${n.data.hex ? `<div class="kv"><span>主色</span><span>${esc(n.data.hex)}</span></div>` : ''}
      ${n.data.origin ? `<div class="kv"><span>设计来源</span><span>${esc(n.data.origin)}</span></div>` : ''}
      ${['template','style','block'].includes(n.kind) && (n.data.preview_url || ['template','style'].includes(n.kind)) ? `<button class="btn btn-primary" style="margin-top:10px" onclick="openNodePreview(${n.id})">查看真实 HTML 预览</button>` : ''}
      <button class="btn btn-danger-ghost" style="margin-top:10px" onclick="delNode(${n.id})">删除节点</button>`;
  }
}
function deleteNodeIds(ids) {
  const removing = new Set(ids);
  for (const workspace of nodes.filter(node => removing.has(node.id) && node.kind === 'ws')) {
    nodes.filter(item => item.workspaceId === workspace.id && !removing.has(item.id)).forEach(item => item.workspaceId = null);
    if (activeWorkspaceId === workspace.id) activeWorkspaceId = null;
  }
  nodes = nodes.filter(node => !removing.has(node.id));
  groups = groups.filter(record => nodes.some(node => node.groupId === record.id));
  edges = edges.filter(edge => !removing.has(edge.from) && !removing.has(edge.to));
  removing.forEach(id => document.getElementById('node-' + id)?.remove());
  selectedIds.clear(); selected = null;
  if (!nodes.some(node => node.kind === 'ws' && node.id === activeWorkspaceId)) activeWorkspaceId = nodes.find(node => node.kind === 'ws')?.id ?? null;
  drawEdges(); save(); timeline(); updateWsCount(); renderWorkspaceNavigator(); renderInspector();
}
function delNode(id) { deleteNodeIds([id]); }
/* ================= 可视化素材库 ================= */
const PALETTE = {
  blocks: () => [{ group:'内容区块 · 拖进工作区' }].concat(BLOCKS.map(b => ({
    id: b.id, t: b.t, mini: miniOf('block', b.id), name: b.t,
    drag: { kind:'block', data:{ title:b.t, blockId:b.id } } })))
    .concat((state.intakeComponents || []).length ? [{ group:'设计吸收 · 组件（审核通过）' }].concat(
      state.intakeComponents.map(c => ({
        id: 'intake-' + c.component_id, t: c.name, name: c.name, en: c.text.slice(0, 60),
        drag: { kind:'block', data:{ title:c.name, text:c.text } } }))) : []),
  layouts: () => [{ group:'版式 · 决定页面骨架' }].concat(LAYOUTS.map(l => ({
    id:l.intent,t:l.t,previewUrl:previewUrl(l.intent,''),previewIntent:l.intent,name:l.t,en:l.intent,
    drag: { kind:'template', data:{ title:l.t, intent:l.intent } } }))),
  styles: () => [{ group:'风格预设' }].concat(state.templates.map(t => ({
    id:t.id,t:t.name,styleCard:true,name:t.name,en:t.origin||'',previewUrl:previewUrl('landing',t.id),
    previewIntent:'landing',previewTemplate:t.id,swatches:[t.tokens.bg,t.tokens.primary,t.tokens.accent],
    drag: { kind:'style', data:{ title:t.name, intent:'landing', preset:t.id, origin:t.origin||'', visual_system:t.visual_system||'', swatches:[t.tokens.bg, t.tokens.primary, t.tokens.accent] } } })))
    .concat([{ group:'色卡 · 主色覆盖' }]).concat(COLORS.map(c => ({
    id: 'color-' + c.id, t: c.t, colorCard: true, name: c.t, sw: c.sw, hex: c.hex,
    drag: { kind:'color', data:{ title:c.t, hex:c.hex, sw:c.sw } } })))
    .concat([{ group:'字体' }]).concat(FONTS.map(f => ({
    id: 'font-' + f.id, t: f.t, fontCard: true, name: f.t, aa: f.aa, fcss: f.css, en: f.en,
    drag: { kind:'font', data:{ title:f.t, font:f.id, css:f.css, en:f.en } } }))),
  files: () => state.projects.length ? [{ group:'项目产物 · 拖出即预览' }].concat(state.projects.map(p => ({
    id: p.name, t: p.name, fileCard: true, name: `${p.intent} · rev${p.revision}`,
    url: p.preview_url,
    drag: { kind:'file', data:{ title:p.name, preview_url:p.preview_url, project:p.project,
      project_name:p.name, intent:p.intent, preset_id:p.preset_id } } })))
    : [{ header:'暂无项目 — 推进一次生成就会出现' }],
  skills: () => state.alliance.length ? [{ group:'Skill 联盟' }].concat(state.alliance.map(s => ({
    id: s.name, t: s.name, name: s.name + (s.installed ? ' ✓' : ' ○'),
    drag: { kind:'skill', data:{ title:s.name, installed:s.installed } } }))) : [{ header:'加载中…' }],
};
let activeTab = 'layouts';
const previewObserver='IntersectionObserver'in window?new IntersectionObserver(entries=>{entries.filter(entry=>entry.isIntersecting).forEach(entry=>{const frame=entry.target;
  if(frame.dataset.src&&!frame.src)frame.src=frame.dataset.src;previewObserver.unobserve(frame);});},{root:$('#pal'),rootMargin:'120px'}):null;
function previewUrl(intent,templateId=''){const params=new URLSearchParams({intent});if(templateId)params.set('template',templateId);return'/api/template-preview?'+params.toString();}
function previewThumb(url,intent,templateId='',title='',galleryId='',galleryPageId=''){return `<div class="template-thumb"><iframe data-src="${esc(url)}" title="${esc(title)} HTML 预览" sandbox="allow-scripts allow-same-origin"></iframe>
  ${galleryId ? '<span class="template-badge">REAL HTML</span>' : ''}<button class="preview-open" type="button" data-preview-intent="${esc(intent)}" data-preview-template="${esc(templateId)}" data-preview-title="${esc(title)}" data-gallery-id="${esc(galleryId)}" data-gallery-page-id="${esc(galleryPageId)}">放大预览</button></div>`;}
function activatePreviewFrames(){document.querySelectorAll('#pal iframe[data-src]').forEach(frame=>{if(previewObserver)previewObserver.observe(frame);else frame.src=frame.dataset.src;});}
function openTemplatePreview(intent,templateId='',title='模板预览'){const url=previewUrl(intent,templateId);$('#preview-pages').hidden=true;$('#preview-pages').innerHTML='';$('#preview-title').textContent=title;
  $('#preview-meta').textContent=INTENT_LABEL[intent]+(templateId?' · '+templateId:'');$('#preview-frame').src=url;window.FoxInteraction?.openDialog('#preview-modal',{initialFocus:'#preview-close'});$('#preview-open-window').onclick=()=>window.open(url,'_blank');}
function closeTemplatePreview(){window.FoxInteraction?.closeDialog('#preview-modal');$('#preview-frame').src='about:blank';$('#preview-pages').hidden=true;$('#preview-pages').innerHTML='';}
$('#preview-close').onclick=closeTemplatePreview;$('#preview-modal').addEventListener('pointerdown',e=>{if(e.target===$('#preview-modal'))closeTemplatePreview();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#preview-modal').hidden)closeTemplatePreview();});
function renderPalette() {
  const q = ($('#search').value || '').trim().toLowerCase();
  const items = PALETTE[activeTab]();
  let html = '';
  for (const it of items) {
    if (it.group) { html += `<div class="pal-group-title">${it.group}</div>`; continue; }
    if (it.header) { html += `<div class="pal-hint">${it.header}</div>`; continue; }
    if (q && !(it.name || '').toLowerCase().includes(q)) continue;
    let preview = '';
    if (it.previewUrl) preview=previewThumb(it.previewUrl,it.previewIntent,it.previewTemplate||'',it.name||it.t,it.galleryId||'',it.galleryPageId||'');
    else if (it.mini) preview = it.mini;
    else if (it.styleCard) preview = `<div class="mini style-card"><div class="row">${it.swatches.slice(0,2).map(c=>`<i style="position:static;flex:1;border-radius:0;background:${c}"></i>`).join('')}</div><div class="aa" style="background:${it.swatches[2]}26">Aa</div></div>`;
    else if (it.colorCard) preview = `<div class="mini" style="display:flex">${it.sw.map(c=>`<i style="position:static;flex:1;border-radius:0;background:${c}"></i>`).join('')}</div>`;
    else if (it.fontCard) preview = `<div class="mini font-card"><span class="aa" style="font-family:${it.fcss}">Aa<small>${it.en}</small></span></div>`;
    else if (it.fileCard) preview = `<div class="file-thumb"><iframe src="${it.url}?t=${Date.now()}" title="${esc(it.t)}产物预览" sandbox="allow-same-origin" tabindex="-1"></iframe></div>`;
    html += `<div class="pal-card ${it.styleCard ? 'style-card' : ''}${it.fontCard ? 'font-card' : ''}${it.galleryCard ? ' gallery-card' : ''}"
      draggable="true" data-pid="${esc(it.id)}" title="拖到工作区，或双击快速加入">${preview}
      <div class="pal-name"><span class="zh">${esc(it.name || it.t)}</span>${it.en ? `<span class="en">${esc(it.en)}</span>` : ''}
      ${it.userGallery ? `<button class="gallery-delete" type="button" data-gallery-delete="${esc(it.galleryId)}" title="删除私人模板">×</button>` : ''}</div></div>`;
  }
  $('#pal').innerHTML = html || '<div class="pal-hint">无匹配</div>';
  activatePreviewFrames();
  document.querySelectorAll('#pal .preview-open').forEach(button=>button.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();if(button.dataset.galleryId)openGalleryPreview(button.dataset.galleryId,button.dataset.galleryPageId||'');else openTemplatePreview(button.dataset.previewIntent,button.dataset.previewTemplate,button.dataset.previewTitle);}));
  document.querySelectorAll('#pal .gallery-delete').forEach(button=>button.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();deleteUserGallery(button.dataset.galleryDelete);}));
  document.querySelectorAll('#pal .pal-card').forEach(cardEl => {
    const pid = cardEl.dataset.pid;
    const item = items.find(i => i.id === pid);
    if (!item) return;
    cardEl.addEventListener('dragstart', e => {
      e.dataTransfer.setData('application/json', JSON.stringify(item.drag));
      e.dataTransfer.effectAllowed = 'copy';
    });
    const addPaletteItem = () => {
      const ws = activeWorkspace() || nodes.filter(n => n.kind === 'ws').pop();
      const [wx, wy] = ws ? [ws.x + 40 + Math.random() * (ws.w - 300), ws.y + 50 + Math.random() * (ws.h - 200)]
                          : toWorld({ clientX: 500, clientY: 300 });
      const n = addNode(item.drag.kind, wx, wy, JSON.parse(JSON.stringify(item.drag.data || {})));
      if (item.drag.kind === 'block' && !n.data.text) n.data.text = BLOCK_TEXT[n.data.blockId] || '';
    };
    cardEl.addEventListener('dblclick', addPaletteItem);
    cardEl.addEventListener('click', () => {
      if (matchMedia('(max-width:760px)').matches || matchMedia('(pointer:coarse)').matches) {
        addPaletteItem(); closeMobilePanels();
      }
    });
  });
}
$('#tabs').addEventListener('click', e => {
  const t = e.target.closest('.tab'); if (!t) return;
  document.querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === t));
  activeTab = t.dataset.tab; updateTemplateImportVisibility(); renderPalette();
});
$('#search').addEventListener('input', renderPalette);
viewport.addEventListener('dragover', e => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; });
viewport.addEventListener('drop', e => {
  e.preventDefault();
  try {
    const d = JSON.parse(e.dataTransfer.getData('application/json'));
    const [wx, wy] = toWorld(e);
    // 落进工作区则吸附到工作区内部
    const ws = nodes.find(n => n.kind === 'ws' && wx > n.x && wx < n.x + n.w && wy > n.y && wy < n.y + n.h);
    const n = addNode(d.kind, Math.round(wx - 110), Math.round(wy - 24), d.data || {});
    if (ws) {
      const settled=canvasEngine.settleNode(n);n.x=settled.x;n.y=settled.y;placeNode(n);
    }
    const dropped = document.getElementById('node-' + n.id);
    if (dropped) { dropped.classList.remove('node-enter'); animateNode(dropped, 'node-drop', 'fox-node-drop'); }
    $('#empty-hint').style.display = 'none';
    updateWsCount(); save();
  } catch (err) {}
});

/* ================= 当前工作区进度 ================= */
const STAGES = ['素材配方', '视觉风格', '需求说明', '需求拆解', '生成产物'];
function timeline() {
  const ws = activeWorkspace();
  if (!ws) {
    $('#tl-title').textContent = '当前工作区'; $('#tl-stages').innerHTML = '';
    $('#tl-status').textContent = '新建工作区后开始创作'; return;
  }
  const recipe = membersOf(ws);
  const artifacts = membersOf(ws, { includeOutputs:true });
  const latestOutput = artifacts.filter(n => n.kind === 'output').sort((a, b) => b.id - a.id)[0];
  const run = ws.data?.recipeRun || latestOutput?.data?.recipe_run;
  if (run?.stages?.length) {
    const statusLabel = {running:'运行中',succeeded:'已完成',failed:'失败'}[run.status] || run.status;
    $('#tl-title').textContent = ws.title + ' · Recipe Run';
    $('#tl-status').textContent = `${statusLabel} · ${run.duration_ms ?? '—'} ms`;
    $('#tl-status').className = 'tl-status' + (run.status === 'succeeded' ? ' ok' : '');
    $('#tl-stages').innerHTML = run.stages.map((stage, index) => {
      const done = ['succeeded','reused'].includes(stage.status);
      const active = stage.status === 'running';
      const failed = stage.status === 'failed';
      return `${index ? `<div class="tl-line ${done || ['succeeded','reused'].includes(run.stages[index - 1]?.status) ? 'done' : ''}"></div>` : ''}
        <div class="tl-stage ${done ? 'done' : active ? 'active' : failed ? 'failed' : ''}">
        <div class="tl-dot">${done ? '✓' : failed ? '!' : index + 1}</div>
        <div class="tl-label">${esc(stage.label || stage.label_en || stage.id)}${stage.duration_ms !== null && stage.duration_ms !== undefined ? ` · ${stage.duration_ms}ms` : ''}</div></div>`;
    }).join('');
    return;
  }
  const requirement = recipe.find(n => n.kind === 'requirement' || n.kind === 'note');
  const done = [
    recipe.some(n => n.kind === 'source' || n.kind === 'block' || n.kind === 'template'),
    recipe.some(n => n.kind === 'style' || n.kind === 'color' || n.kind === 'font' || n.kind === 'template'),
    Boolean(requirement && String(requirement.data?.text || '').trim()),
    Boolean(requirement?.data?.analysis),
    artifacts.some(n => n.kind === 'output'),
  ];
  const active = done.indexOf(false);
  $('#tl-title').textContent = ws.title;
  $('#tl-status').textContent = `${recipe.length} 素材 · ${artifacts.filter(n=>n.kind==='output').length} 产物`;
  $('#tl-status').className = 'tl-status';
  $('#tl-stages').innerHTML = done.map((completed, index) => `
    ${index ? `<div class="tl-line ${done[index - 1] ? 'done' : ''}"></div>` : ''}
    <div class="tl-stage ${completed ? 'done' : index === active ? 'active' : ''}">
      <div class="tl-dot">${completed ? '✓' : index + 1}</div><div class="tl-label">${STAGES[index]}</div></div>`).join('');
}
/* ================= 数据加载 & 初始化 ================= */
async function loadAlliance() {
  try { state.alliance = (await api('/api/alliance')).items; } catch(e) {}
  if (activeTab === 'skills') renderPalette();
}
async function loadTemplates() {
  try { state.templates = (await api('/api/templates')).items; } catch(e) {}
  if (activeTab === 'styles') renderPalette();
}
async function init() {
  /* C7 · 先装上工作台扩展层，再做别的。

     workbench-features.js 现在顶层只有声明：它的三个调色板贡献者与全部 DOM
     绑定都由下面这两行装进来。必须放在 init() 里面而不是文件顶层——classic
     script 的顶层语句在解析时执行，那时 workbench-features.js 还没被解析，
     名字根本不存在；而 `registerWorkbenchPalette?.(PALETTE)` 里的 `?.` 只挡
     null/undefined，挡不住「标识符未声明」的 ReferenceError。
     这一点是被 tests/test_workbench_features_pure.py 抓出来的，不是想出来的。

     由内核显式调用、而不是让 workbench-features.js 自己在顶层改 PALETTE，
     是因为 PALETTE 是本文件的 const，它的值在另一个文件被解析时尚未建好——
     那正是 index.html 里加载顺序曾是硬约束的原因。现在顺序无关紧要，那份文件
     也可以被 Node 单独加载来测纯函数。

     放在最前面，是因为 loadGallery() 稍后会在 Promise.all 里触发
     renderPalette()，那时调色板必须已经注册好。 */
  registerWorkbenchPalette?.(PALETTE);
  bindWorkbenchDom?.();
  window.FoxInteraction?.initialize();
  window.FoxInteraction?.registerDialog('#preview-modal', { onRequestClose:closeTemplatePreview, initialFocus:'#preview-close' });
  window.FoxInteraction?.registerDialog('#export-modal', { onRequestClose:closeExportCenter, initialFocus:'#export-format' });
  window.FoxInteraction?.registerDialog('#create-modal', { onRequestClose:closeCreatePanel, initialFocus:'#creation-prompt' });
  window.FoxInteraction?.registerDialog('#ai-modal', { onRequestClose:closeAISettings, initialFocus:'#ai-enabled' });
  window.FoxInteraction?.registerDialog('#memory-modal', { onRequestClose:closeProjectMemory, initialFocus:'#memory-enabled' });
  window.FoxInteraction?.registerDialog('#intake-modal', { onRequestClose:closeIntake, initialFocus:'#intake-fetch-url' });
  window.FoxInteraction?.registerDialog('#slides-modal', { onRequestClose:closeSlideEditor, initialFocus:'.slides-editor' });
  window.FoxInteraction?.registerDialog('#revision-modal', { onRequestClose:closeRevisionDiff, initialFocus:'#revision-close' });
  updateConnectionStatus();
  const installBtn = $('#btn-install');
  const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  if (isIos && !isStandalone) installBtn.hidden = false;
  installBtn.addEventListener('click', async () => {
    if (deferredInstallPrompt) {
      deferredInstallPrompt.prompt();
      await deferredInstallPrompt.userChoice;
      deferredInstallPrompt = null; installBtn.hidden = true;
    } else {
      alert('iPhone / iPad：请点浏览器“分享”，再选择“添加到主屏幕”。');
    }
  });
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
  try { const h = await (await fetch('/api/health')).json(); $('#ver').textContent = 'v' + h.version; } catch(e) {}
  window.FoxIntake?.preload();
  await Promise.all([loadTemplates(), loadGallery(), loadProjects(), loadAlliance(), loadAISettings(), loadProjectMemory()]);
  let restored = loadSaved();
  if (!restored) restored = await loadRemoteWorkspace();
  if (restored) {
    nodesEl.innerHTML = '';
    nodes.forEach(renderNode); drawEdges(); applyCamera();
    $('#empty-hint').style.display = nodes.length ? 'none' : '';
  } else {
    // 首次进入：预置 PPT 模板工作区（主要内容形态：HTML 载体的 PPT/文档优先）
    const ws = addNode('ws', 40, 60, { title:'工作区 1 · 我的 PPT 模板' });
    const req = addNode('requirement', 90, 130, { title:'需求' });
    req.data.text = '做一个发布会 PPT，主题是 Html九尾狐创作工具，像素花园风格';
    const t = document.getElementById('node-' + req.id); t.querySelector('textarea').value = req.data.text;
    const tpl = addNode('template', 90, 330, { title:'发布会 PPT', intent:'deck' });
    const defaultStyle = state.templates.find(item => item.id === 'fox-pixel-garden') || state.templates[0];
    const st = addNode('style', 350, 130, { title: defaultStyle?.name || '九尾狐 · 像素花园',
      preset: defaultStyle?.id || 'fox-pixel-garden',
      swatches: defaultStyle ? [defaultStyle.tokens.bg, defaultStyle.tokens.primary, defaultStyle.tokens.accent]
                             : ['#FFFDF6', '#173C8F', '#49B894'] });
    const cover = addNode('block', 350, 330, { title:'章节封面', blockId:'cover' });
    select(null);
    $('#empty-hint').style.display = 'none';
  }
  renderPalette(); renderWorkspaceNavigator(); timeline(); updateWsCount();
  window.FoxCanvasProductivity?.initialize();
  applySnapLevel(snapLevel);
  /* 首屏（恢复快照 / 预置工作区）不做入场，只有初始化完成后的新增节点才播 G3 动效 */
  allowNodeEnter = true;
  /* 首屏适配不做相机缓动：缓动期间「渲染位置 ≠ 相机模型」，此刻的指针命中会错位 */
  if (!restored) setTimeout(() => fitAll(false), 120);
}
window.addEventListener('DOMContentLoaded', init);
