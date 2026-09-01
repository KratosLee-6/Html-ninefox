(() => {
  'use strict';

  const DEFAULTS = {
    gridSize: 16,
    alignmentPixels: 7,
    portHitPixels: 32,
    workspacePadding: 16,
    workspaceHeader: 46,
  };

  function create(options) {
    const settings = { ...DEFAULTS, ...(options.settings || {}) };
    const viewport = options.viewport;
    const getCamera = options.getCamera;
    const getNodes = options.getNodes;
    const getNodeElement = options.getNodeElement || (id => document.getElementById('node-' + id));
    const guideX = options.guideX || null;
    const guideY = options.guideY || null;

    function screenToWorld(clientX, clientY) {
      const rect = viewport.getBoundingClientRect();
      const camera = getCamera();
      return [
        (clientX - rect.left - camera.x) / camera.z,
        (clientY - rect.top - camera.y) / camera.z,
      ];
    }

    function nodeSize(node) {
      const element = getNodeElement(node.id);
      return {
        width: Number(node.w) || element?.offsetWidth || 226,
        height: Number(node.h) || element?.offsetHeight || 120,
      };
    }

    function anchors(node, x = node.x, y = node.y) {
      const size = nodeSize(node);
      return {
        x: [x, x + size.width / 2, x + size.width],
        y: [y, y + size.height / 2, y + size.height],
      };
    }

    function bestAlignment(movingAnchors, otherAnchors, threshold) {
      let best = null;
      for (const moving of movingAnchors) {
        for (const other of otherAnchors) {
          const delta = other - moving;
          const distance = Math.abs(delta);
          if (distance <= threshold && (!best || distance < best.distance)) {
            best = { delta, guide: other, distance };
          }
        }
      }
      return best;
    }

    function snapNode(node, rawX, rawY, disabled = false) {
      if (disabled) return { x: rawX, y: rawY, guideX: null, guideY: null };
      const camera = getCamera();
      const threshold = settings.alignmentPixels / camera.z;
      let x = rawX;
      let y = rawY;
      const moving = anchors(node, rawX, rawY);
      let xMatch = null;
      let yMatch = null;
      for (const other of getNodes()) {
        if (other.id === node.id) continue;
        if (node.kind === 'ws' && other.kind !== 'ws') continue;
        const candidate = anchors(other);
        const nextX = bestAlignment(moving.x, candidate.x, threshold);
        const nextY = bestAlignment(moving.y, candidate.y, threshold);
        if (nextX && (!xMatch || nextX.distance < xMatch.distance)) xMatch = nextX;
        if (nextY && (!yMatch || nextY.distance < yMatch.distance)) yMatch = nextY;
      }
      if (xMatch) x += xMatch.delta;
      else x = Math.round(rawX / settings.gridSize) * settings.gridSize;
      if (yMatch) y += yMatch.delta;
      else y = Math.round(rawY / settings.gridSize) * settings.gridSize;
      return {
        x: Math.round(x),
        y: Math.round(y),
        guideX: xMatch?.guide ?? null,
        guideY: yMatch?.guide ?? null,
      };
    }

    function settleNode(node) {
      if (node.kind === 'ws') return { x: node.x, y: node.y, workspaceId: null };
      const size = nodeSize(node);
      const centerX = node.x + size.width / 2;
      const centerY = node.y + Math.min(size.height / 2, 72);
      const workspace = getNodes().find(candidate => candidate.kind === 'ws'
        && centerX >= candidate.x && centerX <= candidate.x + candidate.w
        && centerY >= candidate.y && centerY <= candidate.y + candidate.h);
      if (!workspace) return { x: node.x, y: node.y, workspaceId: null };
      const minX = workspace.x + settings.workspacePadding;
      const maxX = workspace.x + workspace.w - size.width - settings.workspacePadding;
      const minY = workspace.y + settings.workspaceHeader;
      const maxY = workspace.y + workspace.h - size.height - settings.workspacePadding;
      return {
        x: Math.round(Math.min(Math.max(minX, node.x), Math.max(minX, maxX))),
        y: Math.round(Math.min(Math.max(minY, node.y), Math.max(minY, maxY))),
        workspaceId: workspace.id,
      };
    }

    function portPoint(nodeId, side) {
      const node = getNodes().find(item => item.id === nodeId);
      if (!node) return null;
      const element = getNodeElement(nodeId);
      const port = element?.querySelector('[data-port-side="' + side + '"]');
      if (port) {
        return {
          x: node.x + port.offsetLeft + port.offsetWidth / 2,
          y: node.y + port.offsetTop + port.offsetHeight / 2,
        };
      }
      const size = nodeSize(node);
      return { x: node.x + (side === 'out' ? size.width : 0), y: node.y + 30 };
    }

    function nearestInput(clientX, clientY, excludeId) {
      let best = null;
      for (const port of document.querySelectorAll('.port-in[data-port]')) {
        const nodeId = Number(port.dataset.port);
        if (nodeId === excludeId) continue;
        const rect = port.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        const distance = Math.hypot(clientX - x, clientY - y);
        if (distance <= settings.portHitPixels && (!best || distance < best.distance)) {
          best = { nodeId, port, distance };
        }
      }
      return best;
    }

    function edgePath(start, end) {
      const distance = Math.abs(end.x - start.x);
      const bend = Math.max(48, Math.min(220, distance * 0.5));
      const startControl = start.x + bend;
      const endControl = end.x - bend;
      return 'M ' + start.x + ' ' + start.y + ' C ' + startControl + ' ' + start.y
        + ', ' + endControl + ' ' + end.y + ', ' + end.x + ' ' + end.y;
    }

    function showGuides(result) {
      if (guideX) {
        guideX.hidden = result.guideX == null;
        if (result.guideX != null) guideX.style.left = result.guideX + 'px';
      }
      if (guideY) {
        guideY.hidden = result.guideY == null;
        if (result.guideY != null) guideY.style.top = result.guideY + 'px';
      }
    }

    function clearGuides() {
      if (guideX) guideX.hidden = true;
      if (guideY) guideY.hidden = true;
    }

    return {
      screenToWorld,
      nodeSize,
      snapNode,
      settleNode,
      portPoint,
      nearestInput,
      edgePath,
      showGuides,
      clearGuides,
    };
  }

  window.FoxCanvasEngine = { create };
})();
