(() => {
  'use strict';
  if (window.FoxMotion) return;
  const root = document.documentElement;
  const media = matchMedia('(prefers-reduced-motion: reduce)');
  const key = 'fox-motion-preference';
  const modes = ['system', 'reduced', 'off'];
  const active = new Map();
  const tokens = Object.freeze({ feedback:140, enter:180, panel:220, ease:'cubic-bezier(.33,1,.68,1)' });
  let preference = 'system';
  try { const saved = localStorage.getItem(key); if (modes.includes(saved)) preference = saved; } catch (_) {}
  const style = document.createElement('style');
  style.id = 'fox-motion-policy';
  style.textContent = `
    :root { --motion-feedback:140ms; --motion-enter:180ms; --motion-panel:220ms; --motion-ease:cubic-bezier(.33,1,.68,1); }
    :root[data-fox-motion="reduced"] *, :root[data-fox-motion="reduced"] *::before, :root[data-fox-motion="reduced"] *::after,
    :root[data-fox-motion="off"] *, :root[data-fox-motion="off"] *::before, :root[data-fox-motion="off"] *::after {
      animation:none!important; transition:none!important; scroll-behavior:auto!important;
    }
    :root[data-fox-motion]:not([data-fox-motion="full"]) .node.is-generating .node-head::after { display:none; }
    :root[data-fox-hidden="true"] *, :root[data-fox-hidden="true"] *::before, :root[data-fox-hidden="true"] *::after { animation-play-state:paused!important; }
  `;
  document.head.appendChild(style);

  function cancel(scope) { active.get(scope)?.cancel(); }
  function cancelAll() { for (const item of [...active.values()]) item.cancel(); }
  function enabled() { return root.dataset.foxMotion === 'full' && !document.hidden; }
  function sync() {
    root.dataset.foxMotion = preference === 'system' ? (media.matches ? 'reduced' : 'full') : preference;
    root.dataset.foxHidden = String(document.hidden);
    if (!enabled()) cancelAll();
    document.querySelectorAll('[data-motion-preference]').forEach(select => { select.value = preference; });
    window.dispatchEvent(new CustomEvent('fox-motion-change', {detail:{preference, effective:root.dataset.foxMotion}}));
  }
  function setPreference(value) {
    if (!modes.includes(value)) return false;
    preference = value;
    try { localStorage.setItem(key, value); } catch (_) {}
    sync();
    return true;
  }
  function canPlay(element) {
    if (!element?.isConnected || !enabled() || active.size >= 8) return false;
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.right > 0 && rect.top < innerHeight && rect.left < innerWidth;
  }

  // Effects only touch a visual child; canvas/world transforms remain owned by the canvas.
  function play(name, element, scope = element) {
    cancel(scope);
    const effects = {
      reveal:[{opacity:0, transform:'translateY(6px)'}, {opacity:1, transform:'translateY(0)'}],
      panel:[{opacity:0, transform:'translateY(4px)'}, {opacity:1, transform:'translateY(0)'}],
      emphasis:[{opacity:0.55}, {opacity:1}],
    };
    if (!effects[name] || !canPlay(element) || typeof element.animate !== 'function') return {cancel() {}};
    const duration = name === 'panel' ? tokens.panel : name === 'emphasis' ? tokens.feedback : tokens.enter;
    const animation = element.animate(effects[name], {duration, easing:tokens.ease});
    const item = {element, cancel() {
      if (active.get(scope) === item) active.delete(scope);
      animation.cancel();
    }};
    active.set(scope, item);
    animation.finished.then(() => item.cancel(), () => { if (active.get(scope) === item) active.delete(scope); });
    return item;
  }

  // Legacy CSS effects get the same interruption/cleanup guarantees as WAAPI effects.
  function animateClass(element, className, animationName, duration = tokens.enter) {
    cancel(element);
    if (!canPlay(element)) { element?.classList.remove(className); return; }
    let timer;
    const item = {element, cancel() {
      clearTimeout(timer);
      element.removeEventListener('animationend', onEnd);
      element.removeEventListener('animationcancel', onEnd);
      element.classList.remove(className);
      if (active.get(element) === item) active.delete(element);
    }};
    function onEnd(event) { if (event.target === element && event.animationName === animationName) item.cancel(); }
    active.set(element, item);
    element.addEventListener('animationend', onEnd);
    element.addEventListener('animationcancel', onEnd);
    element.classList.add(className);
    timer = setTimeout(item.cancel, duration + 100);
  }
  new MutationObserver(() => {
    for (const item of [...active.values()]) if (!item.element.isConnected) item.cancel();
  }).observe(document.documentElement, {childList:true, subtree:true});
  media.addEventListener('change', sync);
  document.addEventListener('visibilitychange', sync);
  window.addEventListener('pagehide', cancelAll);
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) { preference = modes.includes(event.newValue) ? event.newValue : 'system'; sync(); }
  });
  document.addEventListener('change', event => {
    if (event.target.matches('[data-motion-preference]')) setPreference(event.target.value);
  });
  window.FoxMotion = {tokens, play, animateClass, cancel, cancelAll, enabled, setPreference,
    get preference() { return preference; }, get activeCount() { return active.size; }};
  sync();
})();
