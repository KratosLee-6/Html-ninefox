/* Live edit lifecycle module (v0.8.8 · WYSIWYG A1): click-to-edit text
 * inside an artifact's preview iframe, for every intent — not just decks.
 *
 * Contract with the server (tests/test_live_edit.py guards both sides):
 *   GET  /api/projects/<name>/text-nodes → {nodes:[{slide,node,text}], revision}
 *   PUT  /api/projects/<name>/text       → {edits:[{slide,node,text,current}],
 *                                           expected_revision} → new revision
 * The frontend walker enumerates visible text nodes in document order with
 * the same filters as the server mapper (skip script/style, skip blank);
 * `node` indexes must line up, and `current` is verified server-side before
 * any span is replaced — misalignment fails loudly instead of editing the
 * wrong node (edit/preview consistency, the v0.7.4 lesson).
 * Every save creates a NEW revision; history is never overwritten. */
(function () {
  'use strict';

  const active = new Map();    /* nodeId → session */
  const bound = new WeakSet(); /* 已绑过点击的父元素：重复 enter 不双绑 */

  /* Same filters as pptx_export._TextNodeMapper: document order, skip
   * script/style, skip whitespace-only nodes. */
  function walkTextNodes(root) {
    const out = [];
    const walker = root.createTreeWalker(root.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;
        const tag = parent.tagName.toLowerCase();
        if (tag === 'script' || tag === 'style') return NodeFilter.FILTER_REJECT;
        if (!node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    for (let current = walker.nextNode(); current; current = walker.nextNode()) {
      out.push(current);
    }
    return out;
  }

  function injectStyles(doc) {
    if (doc.getElementById('fox-live-style')) return;
    const style = doc.createElement('style');
    style.id = 'fox-live-style';
    style.textContent =
      '.fox-live-editing [data-fox-live] { cursor: text; border-radius: 2px; }' +
      '.fox-live-editing [data-fox-live]:hover { outline: 2px dashed #3b82f6;' +
      '  outline-offset: 2px; background: rgba(59,130,246,.08); }' +
      '.fox-live-editing [data-fox-live].fox-live-active { outline: 2px solid #3b82f6;' +
      '  outline-offset: 2px; background: rgba(59,130,246,.06); }';
    doc.head.appendChild(style);
  }

  function exit(nodeId, { silent = false } = {}) {
    const session = active.get(nodeId);
    if (!session) return;
    active.delete(nodeId);
    session.frame?.removeEventListener('load', session.onFrameLoad);
    const doc = session.frame?.contentDocument;
    if (doc?.body) {
      doc.body.classList.remove('fox-live-editing');
      doc.querySelectorAll('[data-fox-live]').forEach(el => {
        el.removeAttribute('data-fox-live');
        el.classList.remove('fox-live-active');
        el.contentEditable = 'false';
      });
    }
    if (!silent) flash('已退出点选编辑', true, 'info');
  }

  async function enter(node) {
    const frame = document.querySelector(`#frame-${node.id}`);
    if (!frame?.contentDocument?.body) {
      return flash('预览尚未加载完成，稍后再试', false);
    }
    const projectName = node.data.project_name;
    const listing = await api('/api/projects/' + encodeURIComponent(projectName) + '/text-nodes');
    const doc = frame.contentDocument;
    const domNodes = walkTextNodes(doc);
    /* 一致性闸门：DOM 枚举与服务器映射表必须一一对应——数目对不上时
     * 宁可拒绝进入编辑（照实说），也不冒改错节点的风险。 */
    if (domNodes.length !== listing.nodes.length) {
      return flash(`编辑器与产物文本不一致（DOM ${domNodes.length} ≠ 映射 ${listing.nodes.length}），请刷新后重试`, false);
    }
    const session = {
      nodeId: node.id, projectName, frame,
      revision: listing.revision,
      records: new Map(),   /* parent element → {node, slide, text} */
      onFrameLoad: null,
    };
    doc.body.classList.add('fox-live-editing');
    domNodes.forEach((textNode, index) => {
      const parent = textNode.parentElement;
      if (!parent) return;
      parent.setAttribute('data-fox-live', String(listing.nodes[index].node));
      if (!bound.has(parent)) {
        bound.add(parent);
        parent.addEventListener('click', event => onTextClick(event, session, parent), { capture: true });
      }
      /* reload 后元素是新的，records 每次进入都重建 */
      session.records.set(parent, {
        node: listing.nodes[index].node,
        slide: listing.nodes[index].slide,
        text: listing.nodes[index].text,
      });
    });
    /* 保存成功后 iframe 会重载；load 后若会话仍在，自动重新进入编辑态 */
    session.onFrameLoad = () => {
      if (active.get(node.id) === session) {
        const fresh = nodes.find(item => item.id === node.id);
        if (fresh) void enter(fresh);
      }
    };
    frame.addEventListener('load', session.onFrameLoad, { once: true });
    active.set(node.id, session);
    flash(`✎ 点选编辑：单击文字直接改，Enter 保存 · Esc 取消（基于 rev${listing.revision}）`, true, 'info');
  }

  function onTextClick(event, session, parent) {
    if (parent.isContentEditable) return;   /* 已在编辑中 */
    const record = session.records.get(parent);
    if (!record) return;
    event.preventDefault();
    event.stopPropagation();
    parent.contentEditable = 'true';
    parent.classList.add('fox-live-active');
    parent.focus();
    /* 点选语义：进入编辑即整段全选——直接打字=整段替换；想局部微调，
     * 再点一次会把光标落到点击处（isContentEditable 分支放行默认行为）。 */
    const selection = parent.ownerDocument.getSelection();
    const range = parent.ownerDocument.createRange();
    range.selectNodeContents(parent);
    selection.removeAllRanges();
    selection.addRange(range);
    const finish = async () => {
      parent.removeEventListener('blur', onBlur);
      parent.removeEventListener('keydown', onKey);
      parent.contentEditable = 'false';
      parent.classList.remove('fox-live-active');
      const next = (parent.textContent || '').replace(/\s+/g, ' ').trim();
      if (next === record.text) return;   /* 未改动或 Esc 后原样 */
      await commit(session, record, next);
    };
    const onBlur = () => { void finish(); };
    const onKey = (keyEvent) => {
      if (keyEvent.key === 'Escape') {
        parent.removeEventListener('blur', onBlur);
        parent.removeEventListener('keydown', onKey);
        parent.contentEditable = 'false';
        parent.classList.remove('fox-live-active');
        parent.textContent = record.text;   /* 还原现文，不产生保存 */
      } else if (keyEvent.key === 'Enter' && !keyEvent.shiftKey) {
        keyEvent.preventDefault();
        parent.blur();
      }
    };
    parent.addEventListener('blur', onBlur);
    parent.addEventListener('keydown', onKey);
  }

  async function commit(session, record, nextText) {
    try {
      const result = await api('/api/projects/' + encodeURIComponent(session.projectName) + '/text', 'PUT', {
        edits: [{ slide: record.slide, node: record.node, text: nextText, current: record.text }],
        expected_revision: session.revision,
      });
      session.revision = result.revision;
      /* 唯一写回协议（C2）：徽章 / iframe 刷新 / 检查器 / 工作区持久化
       * 全部归 advanceNodeRevision——不在这里手搓第二份。 */
      await window.FoxRevisions.advanceNodeRevision(session.nodeId, result.revision);
      flash(`✓ 已保存为 rev${result.revision}，继续点选可接着改`, true);
    } catch (error) {
      if (error.code === 'revision_conflict' || error.code === 'text_node_mismatch'
          || error.code === 'text_edit_noop') {
        exit(session.nodeId, { silent: true });
        flash(error.message + '（已退出编辑模式）', false);
      } else {
        flash('保存失败：' + error.message, false);
      }
    }
  }

  async function toggle(nodeId) {
    const node = nodes.find(item => item.id === nodeId);
    if (!node?.data?.project_name) return flash('该产物缺少项目信息', false);
    if (active.has(nodeId)) return exit(nodeId);
    try {
      await enter(node);
    } catch (error) {
      active.delete(nodeId);
      flash('进入编辑失败：' + error.message, false);
    }
  }

  window.FoxLiveEdit = { toggle, exit, isActive: id => active.has(id) };
})();
