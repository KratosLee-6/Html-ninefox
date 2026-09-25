/* Generation lifecycle module: advance pipeline, job polling, progress rings,
 * partial rerun, and generation cancel/abandon tracking.
 * One in-flight generation per workspace: rapid re-entry is rejected, stale
 * results are dropped, and waiting can be cancelled at any stage. */
(function () {
  'use strict';

  /* ---- progress rings (G5): real job.progress only; no fake progress ---- */
  const generatingNodes = new Map();     /* nodeId -> { pct:number|null, status:'running'|'failed' } */
  const generationCleanups = new Map();

  function cancelCleanup(nodeId) {
    generationCleanups.get(nodeId)?.();
    generationCleanups.delete(nodeId);
  }

  function renderBadge(el, n) {
    const state = generatingNodes.get(n.id);
    if (!state) return;
    el.classList.toggle('is-generating', state.status === 'running');
    el.classList.toggle('is-gen-failed', state.status === 'failed');
    const headEl = el.querySelector('.node-head');
    if (!headEl) return;
    let ring = headEl.querySelector('[data-gen-ring]');
    if (!ring) {
      ring = document.createElement('span');
      ring.className = 'gen-ring';
      ring.setAttribute('data-gen-ring', '');
      ring.innerHTML = '<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true">'
        + '<circle class="gen-ring-track" cx="10" cy="10" r="8" pathLength="1"></circle>'
        + '<circle class="gen-ring-bar" cx="10" cy="10" r="8" pathLength="1"></circle></svg>'
        + '<b class="gen-ring-pct"></b>';
      headEl.appendChild(ring);
    }
    const bar = ring.querySelector('.gen-ring-bar');
    const label = ring.querySelector('.gen-ring-pct');
    if (state.status === 'failed') {
      ring.dataset.mode = 'failed';
      bar.style.strokeDasharray = '1';
      bar.style.strokeDashoffset = '0';
      label.textContent = '失败';
      return;
    }
    if (state.pct == null) {
      ring.dataset.mode = 'spin';
      bar.style.strokeDasharray = '.25 1';
      bar.style.strokeDashoffset = '0';
      label.textContent = '…';
      return;
    }
    ring.dataset.mode = 'progress';
    const pct = Math.max(0, Math.min(100, Math.round(Number(state.pct) || 0)));
    bar.style.strokeDasharray = '1';
    bar.style.strokeDashoffset = String(1 - pct / 100);
    label.textContent = pct + '%';
  }

  function mark(nodeId, pct = null) {
    cancelCleanup(nodeId);
    const el = document.getElementById('node-' + nodeId);
    const node = nodes.find(item => item.id === nodeId);
    if (!el || !node || !el.querySelector('.node-head')) return;   /* 没有标题栏的节点（工作区）不挂进度环 */
    generatingNodes.set(nodeId, { pct, status: 'running' });
    el.classList.remove('is-gen-failed', 'is-gen-done');
    el.classList.add('is-generating');
    renderBadge(el, node);
  }

  function finish(nodeId, failed = false) {
    cancelCleanup(nodeId);
    const el = document.getElementById('node-' + nodeId);
    const node = nodes.find(item => item.id === nodeId);
    if (!el || !node) { generatingNodes.delete(nodeId); return; }
    if (failed) {
      const failedState = { pct: null, status: 'failed' };
      generatingNodes.set(nodeId, failedState);
      renderBadge(el, node);
      el.classList.remove('is-generating');
      el.classList.add('is-gen-failed');
      const timer = setTimeout(() => {
        generationCleanups.delete(nodeId);
        if (generatingNodes.get(nodeId) !== failedState) return;
        generatingNodes.delete(nodeId);
        const current = document.getElementById('node-' + nodeId);
        current?.querySelector('[data-gen-ring]')?.remove();
        current?.classList.remove('is-gen-failed');
      }, 2600);
      generationCleanups.set(nodeId, () => clearTimeout(timer));
      return;
    }
    const ring = el.querySelector('[data-gen-ring]');
    generatingNodes.delete(nodeId);
    el.classList.remove('is-generating');
    el.classList.add('is-gen-done');
    let timer;
    const dispose = () => { clearTimeout(timer); ring?.removeEventListener('animationend', onEnd); };
    const cleanup = () => {
      dispose(); generationCleanups.delete(nodeId);
      if (generatingNodes.has(nodeId)) return;
      document.getElementById('node-' + nodeId)?.querySelector('[data-gen-ring]')?.remove();
      document.getElementById('node-' + nodeId)?.classList.remove('is-gen-done');
    };
    const onEnd = event => { if (event.target === ring && event.animationName === 'fox-gen-done') cleanup(); };
    if (ring && window.FoxMotion?.enabled()) {
      ring.addEventListener('animationend', onEnd);
      timer = setTimeout(cleanup, 400);
      generationCleanups.set(nodeId, dispose);
    } else cleanup();
  }

  /* Quietly clear ring state after cancel/abandon: no failure color, no done pulse. */
  function resetNode(nodeId) {
    cancelCleanup(nodeId);
    generatingNodes.delete(nodeId);
    const el = document.getElementById('node-' + nodeId);
    el?.querySelector('[data-gen-ring]')?.remove();
    el?.classList.remove('is-generating', 'is-gen-failed', 'is-gen-done');
  }

  /* ---- in-flight tracking: one generation per workspace ---- */
  const activeJobs = new Map();   /* wsId -> { jobId:string|null, nodeId, abandoned:boolean } */

  function syncCancelControl() {
    const btn = document.getElementById('btn-cancel-gen');
    if (btn) btn.hidden = activeJobs.size === 0;
  }

  async function waitForJob(jobId, onUpdate, guard) {
    while (true) {
      if (guard && guard()) throw { abandoned: true, message: '已停止等待' };
      const job = await api('/api/jobs/' + encodeURIComponent(jobId));
      if (guard && guard()) throw { abandoned: true, message: '已停止等待' };
      onUpdate && onUpdate(job);
      if (job.status === 'succeeded') return job.result;
      if (job.status === 'failed') throw new Error(job.error?.message || '生成任务失败');
      if (job.status === 'cancelled') { const e = new Error('生成任务已取消'); e.cancelled = true; throw e; }
      await delay(450);
    }
  }

  function progressReporter(label) {
    let lastStage = null;
    const names = { queued: '排队', analyze: '分析需求', compose: '组合输入', generate: '生成产物', verify: '质量验证', deliver: '保存产物', completed: '完成' };
    return job => {
      const stage = job.stage || job.status || 'queued';
      const progress = job.progress == null ? '' : ' · ' + Math.max(0, Math.min(100, Number(job.progress) || 0)) + '%';
      const message = label + ' · ' + (names[stage] || stage) + progress;
      const status = $('#tl-status');
      status.textContent = message; status.className = 'tl-status';
      if (stage !== lastStage) {
        window.FoxInteraction?.notify(label + ' · ' + (names[stage] || stage), 'info');
        lastStage = stage;
      }
    };
  }

  function setAn(req, html) {
    const el = document.getElementById('an-' + req.id);
    if (el) el.innerHTML = html;
  }

  function anChips(an) {
    if (!an) return '';
    return `<span>${INTENT_LABEL[an.intent]}</span><span>${an.preset_id}</span>` +
      (an.memory_applied?.applied?.length ? `<span class="dim">记忆 ${an.memory_applied.applied.length} 项</span>` : '') +
      (an.tone ? `<span class="dim">${esc(an.tone)}</span>` : '') +
      (an.brand && an.brand !== 'Your Product' ? `<span class="dim">${esc(an.brand)}</span>` : '') +
      `<span class="dim">${Math.round((an.confidence || 0) * 100)}%</span>`;
  }

  async function advanceActive() {
    const ws = activeWorkspace();
    if (!ws) return flash('画布上还没有工作区 — 点 HUD 的 ▣ 新建', false);
    return advance(ws.id);
  }

  async function advance(wsId, options = {}) {
    const ws = nodes.find(n => n.id === wsId);
    if (!ws) return;
    const existing = activeJobs.get(wsId);
    if (existing) return flash('该工作区正在推进，请等待完成或点「取消生成」', false);
    const entry = { jobId: null, nodeId: null, abandoned: false };
    activeJobs.set(wsId, entry);
    syncCancelControl();
    activeWorkspaceId = ws.id; renderWorkspaceNavigator(); timeline();
    const members = membersOf(ws);
    const req = members.find(n => n.kind === 'requirement') || members.find(n => n.kind === 'note');
    const btn = document.getElementById('ws-go-' + wsId);
    const inputIds = Array.isArray(req?.data?.input_ids) ? req.data.input_ids : [];
    if (!req || (!(req.data.text || '').trim() && !inputIds.length)) {
      activeJobs.delete(wsId); syncCancelControl();
      return flash('请先点顶部“输入需求”，填写文字或添加文件/图片', false);
    }
    entry.nodeId = req.id;
    const primaryButton = document.getElementById('btn-go');
    window.FoxInteraction?.setBusy(btn, true, '推进中…');
    window.FoxInteraction?.setBusy(primaryButton, true, '推进中…');
    const guard = () => entry.abandoned;
    const bailIfAbandoned = () => { if (entry.abandoned) throw { abandoned: true, message: '已停止等待' }; };
    try {
      /* 阶段 1 · 需求拆解 */
      setAn(req, `<span class="spin">拆解中…</span>`);
      mark(req.id, null);   /* G5：拆解阶段没有真实百分比 → 不定进度环 */
      const analyzePayload = { prompt: req.data.text || '', inputs: inputIds };
      const an = options.analysis || await post('/api/analyze', analyzePayload);
      bailIfAbandoned();
      req.data.analysis = an;
      setAn(req, anChips(an));
      flash(`拆解 ✓ ${INTENT_LABEL[an.intent]} · 风格 ${an.preset_id} · ${an.engine === 'llm' ? 'AI' : '规则'} · 置信度 ${an.confidence}`, true);

      /* 阶段 2 · 读取用户实际组合 */
      const tplNode = members.find(n => n.kind === 'template');
      let intent = (tplNode && tplNode.data.intent) || an.intent;
      if (tplNode && tplNode.data.intent !== an.intent && (an.intent_confidence || 0) >= 0.55) {
        intent = an.intent;
        flash(`需求指向${INTENT_LABEL[an.intent]}，已按需求类型生成（所选页面配方继续生效）`, true);
      }
      const styleNode = members.find(n => n.kind === 'style');
      const colorNode = members.find(n => n.kind === 'color');
      const fontNode = members.find(n => n.kind === 'font');
      const skillNode = members.find(n => n.kind === 'skill');
      const blockNodes = members.filter(n => n.kind === 'block');
      const blockTexts = blockNodes.map(n => (n.data.text || '').trim()).filter(Boolean);
      const blocks = [...new Set(blockNodes.map(n => n.data.blockId).filter(Boolean))];
      const galleryId = tplNode?.data?.gallery_id || blockNodes.find(n => n.data.gallery_id)?.data.gallery_id || null;
      const body = {
        prompt: [String(req.data.text || '').trim() || '请根据上传附件生成合适的 HTML 作品', ...blockTexts].join('\n'),
        inputs: inputIds,
        intent,
        template: (styleNode && styleNode.data.preset) || (tplNode && (tplNode.data.template || tplNode.data.preset)) || null,
        gallery_id: galleryId,
        blocks,
        skill: skillNode && skillNode.data.title,
        primary: colorNode && colorNode.data.hex,
        font: fontNode && fontNode.data.font,
        selection_mode: options.selectionMode || (galleryId || blocks.length ? 'custom' : 'automatic'),
        quiet_llm: false,
      };

      /* 阶段 3 · 异步生成 */
      const submitted = await api('/api/jobs', 'POST', body);
      bailIfAbandoned();
      entry.jobId = submitted.job.id;
      const reportProgress = progressReporter('生成');
      const d = await waitForJob(submitted.job.id, job => {
        const pct = Number(job.progress || 0);
        window.FoxInteraction?.setBusy(btn, true, '生成 ' + pct + '%');
        window.FoxInteraction?.setBusy(primaryButton, true, '生成 ' + pct + '%');
        if (job.recipe_run) { ws.data.recipeRun = job.recipe_run; timeline(); }
        mark(req.id, pct);   /* G5：真实 job.progress 喂进度环 */
        reportProgress(job);
      }, guard);
      finish(req.id, false);
      const out = addNode('output', ws.x + ws.w + 80, ws.y + 30,
        {
          workspaceId: ws.id, title: INTENT_LABEL[d.intent] + ' · 产物', preview_url: d.preview_url, project: d.project,
          project_name: d.project_name, intent: d.intent, preset_id: d.preset_id, revision: 0, feedback: [],
          gallery_id: galleryId, blocks, selection_mode: body.selection_mode,
          recipe_run: d.recipe_run, verification: d.verification, memory_applied: d.memory_applied
        });
      if (!edges.some(e => e.from === req.id && e.to === out.id)) edges.push({ from: req.id, to: out.id });
      ws.data.recipeRun = d.recipe_run || ws.data.recipeRun;
      drawEdges(); select(out.id);
      const outputFrame = document.getElementById('frame-' + out.id);
      outputFrame?.addEventListener('load', () => window.FoxMotion?.play('reveal', outputFrame, 'output:' + out.id), { once: true });
      flash(`✓ ${INTENT_LABEL[d.intent]} · ${d.preset_id} · ${d.route_decision} · rev0`, true);
      window.FoxProjects?.load();
      loadProjectMemory();
      if (d.memory_applied?.applied?.length) flash('项目记忆已复用 ' + d.memory_applied.applied.length + ' 项；本次明确要求优先', true);
      fitRect(Math.min(ws.x, out.x) - 30, ws.y - 10,
        ws.w + (out.x - ws.x) + out.w + 60, ws.h + 40);
      await persistWorkspaceNow();
    } catch (e) {
      if (e && e.abandoned) {
        setAn(req, '');
        resetNode(req.id);
        flash('已停止等待本次生成，任务仍在后台完成；结果稍后出现在项目列表', true, 'info');
      } else if (e && e.cancelled) {
        setAn(req, '');
        resetNode(req.id);
        flash('生成任务已取消', true, 'info');
      } else {
        flash('✗ ' + e.message, false); setAn(req, '');
        finish(req.id, true);   /* G5：失败 → 陶土橙 #E57A3F */
      }
    } finally {
      activeJobs.delete(wsId);
      syncCancelControl();
      window.FoxInteraction?.setBusy(btn, false);
      window.FoxInteraction?.setBusy(primaryButton, false);
    }
  }

  async function cancel(wsId) {
    const entry = activeJobs.get(wsId);
    if (!entry) return;
    entry.abandoned = true;
    if (!entry.jobId) return;   /* 尚未提交：推进流程会在下一个 await 点自行退出 */
    try {
      await api('/api/jobs/' + encodeURIComponent(entry.jobId), 'DELETE');
    } catch (e) {
      if (e.status === 409) return;   /* 已在执行，无法安全中断：保持“停止等待”语义 */
      throw e;
    }
  }

  async function cancelActive() {
    for (const wsId of [...activeJobs.keys()]) await cancel(wsId);
  }

  function isBusy(wsId) { return activeJobs.has(wsId); }

  async function rerun(nodeId, stage) {
    const node = nodes.find(item => item.id === nodeId);
    if (!node?.data?.project_name) return flash('产物缺少项目信息，无法局部重跑', false);
    try {
      mark(node.id, null);   /* G5：局部重跑同样走进度环 */
      const submitted = await api('/api/projects/' + encodeURIComponent(node.data.project_name) + '/recipe-rerun', 'POST', { stage });
      const reportProgress = progressReporter('局部重跑');
      const result = await waitForJob(submitted.job.id, job => {
        mark(node.id, Number(job.progress || 0));
        if (job.recipe_run) {
          node.data.recipe_run = job.recipe_run;
          const ws = workspaceForNode(node);
          if (ws) ws.data.recipeRun = job.recipe_run;
          updateRecipeRunView(job.recipe_run);
          timeline();
        }
        reportProgress(job);
      });
      finish(node.id, false);
      node.data.recipe_run = result.recipe_run;
      node.data.verification = result.verification;
      node.data.revision = result.revision;
      const revisionBadge = document.querySelector(`#rev-${node.id}`);
      if (revisionBadge) revisionBadge.textContent = 'rev' + result.revision;
      const preview = document.querySelector(`#frame-${node.id}`);
      if (preview && stage === 'generate') preview.src = node.data.preview_url + '?t=' + Date.now();
      const ws = workspaceForNode(node);
      if (ws) ws.data.recipeRun = result.recipe_run;
      renderInspector();
      timeline();
      await persistWorkspaceNow();
      flash(`✓ ${stage === 'verify' ? '质量验证' : '产物生成'} 已局部重跑`, true);
    } catch (error) {
      flash('局部重跑失败：' + error.message, false);
      finish(node.id, true);
      renderInspector();
    }
  }

  window.FoxGeneration = {
    generatingNodes, generationCleanups,
    renderBadge, mark, finish, resetNode, cancelCleanup,
    advanceActive, advance, waitForJob, progressReporter,
    rerun, cancel, cancelActive, isBusy,
  };
})();
