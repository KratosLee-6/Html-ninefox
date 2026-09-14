(() => {
  'use strict';

  const DEFAULTS = {
    gridSize: 16,
    alignmentPixels: 7,
    alignmentReleasePixels: 14,
    portHitPixels: 48,
    portReleasePixels: 76,
    nodeCapturePixels: 18,
    workspacePadding: 16,
    workspaceHeader: 46,
  };

  /* G1 · 网格吸附档位：8 / 16 / 32 / 0（0 = 关闭，只保留对齐线） */
  const SNAP_LEVELS = [8, 16, 32, 0];

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
      movingAnchors.forEach((moving, movingIndex) => {
        otherAnchors.forEach((other, otherIndex) => {
          const delta = other - moving;
          const distance = Math.abs(delta);
          if (distance <= threshold && (!best || distance < best.distance)) {
            best = { delta, guide:other, distance, movingIndex, otherIndex };
          }
        });
      });
      return best;
    }

    function lockedAlignment(movingAnchors, lock, threshold) {
      if (!lock || movingAnchors[lock.movingIndex] == null) return null;
      const delta = lock.guide - movingAnchors[lock.movingIndex];
      const distance = Math.abs(delta);
      if (distance > threshold) return null;
      return { ...lock, delta, distance };
    }

    function createSnapSession() {
      return { x:null, y:null };
    }

    function snapNode(node, rawX, rawY, disabledOrOptions = false, excludeIds = []) {
      const options = typeof disabledOrOptions === 'object'
        ? { grid:true, gridSize:settings.gridSize, excludeIds:[], ...disabledOrOptions }
        : { disabled:Boolean(disabledOrOptions), grid:true, gridSize:settings.gridSize, excludeIds };
      const session = options.session || null;
      if (options.disabled) {
        if (session) { session.x = null; session.y = null; }
        return { x:rawX, y:rawY, guideX:null, guideY:null };
      }
      const excluded = new Set(options.excludeIds || []);
      const camera = getCamera();
      const gridSize = Number(options.gridSize) > 0 ? Number(options.gridSize) : settings.gridSize;
      const gridThreshold = Number(options.gridThreshold) > 0 ? Number(options.gridThreshold) / camera.z : null;
      const threshold = settings.alignmentPixels / camera.z;
      const releaseThreshold = settings.alignmentReleasePixels / camera.z;
      let x = rawX;
      let y = rawY;
      const moving = anchors(node, rawX, rawY);
      let xMatch = lockedAlignment(moving.x, session?.x, releaseThreshold);
      let yMatch = lockedAlignment(moving.y, session?.y, releaseThreshold);
      for (const other of getNodes()) {
        if (other.id === node.id || excluded.has(other.id)) continue;
        if (node.kind === 'ws' && other.kind !== 'ws') continue;
        const candidate = anchors(other);
        if (!xMatch) {
          const nextX = bestAlignment(moving.x, candidate.x, threshold);
          if (nextX && (!xMatch || nextX.distance < xMatch.distance)) xMatch = nextX;
        }
        if (!yMatch) {
          const nextY = bestAlignment(moving.y, candidate.y, threshold);
          if (nextY && (!yMatch || nextY.distance < yMatch.distance)) yMatch = nextY;
        }
      }
      if (session) {
        session.x = xMatch ? { guide:xMatch.guide, movingIndex:xMatch.movingIndex, otherIndex:xMatch.otherIndex } : null;
        session.y = yMatch ? { guide:yMatch.guide, movingIndex:yMatch.movingIndex, otherIndex:yMatch.otherIndex } : null;
      }
      /* 对齐线吸附（7px 强吸）优先；无对齐候选时才回落到网格取整（档位 gridSize，0 或 grid:false 表示关闭）。
         gridThreshold 只给拖动热路径用：离网格线较远时保持原始位置，避免拖动中跳动；落位不传则按整数倍硬取整。 */
      const resolve = (raw, match) => {
        if (match) return raw + match.delta;
        if (options.grid === false) return raw;
        const snapped = Math.round(raw / gridSize) * gridSize;
        if (gridThreshold != null && Math.abs(snapped - raw) > gridThreshold) return raw;
        return snapped;
      };
      x = resolve(rawX, xMatch);
      y = resolve(rawY, yMatch);
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
        const rect = port.getBoundingClientRect();
        if (rect.width || rect.height) {
          const point = screenToWorld(rect.left + rect.width / 2, rect.top + rect.height / 2);
          return { x:point[0], y:point[1] };
        }
      }
      const size = nodeSize(node);
      return { x: node.x + (side === 'out' ? size.width : 0), y: node.y + 30 };
    }

    function pointRectDistance(clientX, clientY, rect, padding = 0) {
      const left = rect.left - padding;
      const right = rect.right + padding;
      const top = rect.top - padding;
      const bottom = rect.bottom + padding;
      const dx = Math.max(left - clientX, 0, clientX - right);
      const dy = Math.max(top - clientY, 0, clientY - bottom);
      return Math.hypot(dx, dy);
    }

    function inputMetrics(port, clientX, clientY, padding = settings.nodeCapturePixels) {
      const portRect = port.getBoundingClientRect();
      const nodeElement = port.closest('.node');
      const nodeRect = nodeElement?.getBoundingClientRect();
      if (!nodeRect || (!portRect.width && !portRect.height)) return null;
      const portX = portRect.left + portRect.width / 2;
      const portY = portRect.top + portRect.height / 2;
      return {
        portDistance:Math.hypot(clientX - portX, clientY - portY),
        cardDistance:pointRectDistance(clientX, clientY, nodeRect, padding),
        nodeRect, portX, portY, nodeElement,
      };
    }

    function inputScore(metrics, sourceNode, targetNode, sourceRect) {
      let score = metrics.cardDistance === 0 ? Math.min(metrics.portDistance, 10) : metrics.portDistance;
      if (sourceNode?.workspaceId && sourceNode.workspaceId === targetNode?.workspaceId) score -= 7;
      if (sourceRect && metrics.portX < sourceRect.right - 20) score += 10;
      return score;
    }

    function nearestInput(clientX, clientY, excludeId, currentTarget = null) {
      const sourceNode = getNodes().find(item => item.id === excludeId);
      const sourceElement = sourceNode ? getNodeElement(sourceNode.id) : null;
      const sourceRect = sourceElement?.getBoundingClientRect();
      let sticky = null;
      if (currentTarget?.port?.isConnected) {
        const metrics = inputMetrics(currentTarget.port, clientX, clientY, settings.nodeCapturePixels + 10);
        if (metrics && (metrics.portDistance <= settings.portReleasePixels || metrics.cardDistance === 0)) {
          const targetNode = getNodes().find(item => item.id === currentTarget.nodeId);
          const capture = metrics.portDistance <= settings.portHitPixels ? 'port' : 'node';
          sticky = { ...currentTarget, distance:metrics.portDistance,
            score:inputScore(metrics, sourceNode, targetNode, sourceRect), capture };
        }
      }
      let best = null;
      for (const port of document.querySelectorAll('.port-in[data-port]')) {
        const nodeId = Number(port.dataset.port);
        if (nodeId === excludeId) continue;
        const targetNode = getNodes().find(item => item.id === nodeId);
        if (!targetNode || targetNode.locked) continue;
        const metrics = inputMetrics(port, clientX, clientY);
        if (!metrics) continue;
        const insideCard = metrics.cardDistance === 0;
        if (metrics.portDistance > settings.portHitPixels && !insideCard) continue;
        const score = inputScore(metrics, sourceNode, targetNode, sourceRect);
        if (!best || score < best.score || (score === best.score && metrics.portDistance < best.distance)) {
          const capture = metrics.portDistance <= settings.portHitPixels ? 'port' : 'node';
          best = { nodeId, port, distance:metrics.portDistance, score, capture };
        }
      }
      if (!sticky) return best;
      if (!best) return sticky;
      if (best.nodeId === sticky.nodeId) return best;
      const exactPort = best.capture === 'port' && best.distance <= settings.portHitPixels * 0.55;
      if (exactPort || best.score + 14 < sticky.score) return best;
      return sticky;
    }

    function edgePath(start, end) {
      const horizontal = Math.abs(end.x - start.x);
      const vertical = Math.abs(end.y - start.y);
      const bend = Math.max(56, Math.min(260, horizontal * 0.48 + vertical * 0.16));
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
      createSnapSession,
      snapNode,
      settleNode,
      portPoint,
      nearestInput,
      edgePath,
      showGuides,
      clearGuides,
    };
  }

  window.FoxCanvasEngine = { create, snapLevels:SNAP_LEVELS, defaultGridSize:DEFAULTS.gridSize };
})();
