(() => {
  'use strict';

  const commands = new Map();
  const dialogs = new Map();
  const dialogStack = [];
  const dialogOpeners = new WeakMap();
  const busyStates = new WeakMap();
  const recentMessages = new Map();
  let initialized = false;
  let toastSequence = 0;

  const focusableSelector = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(',');

  function elementOf(target) {
    if (typeof target === 'string') return document.querySelector(target);
    return target || null;
  }

  function ensureToastRegion() {
    let region = document.getElementById('toast-region');
    if (region) return region;
    region = document.createElement('div');
    region.id = 'toast-region';
    region.className = 'toast-region';
    region.setAttribute('role', 'status');
    region.setAttribute('aria-live', 'polite');
    region.setAttribute('aria-atomic', 'false');
    document.body.appendChild(region);
    return region;
  }

  function notificationType(type) {
    return ['success', 'info', 'warning', 'error'].includes(type) ? type : 'info';
  }

  function notify(message, type = 'info', options = {}) {
    const text = String(message || '').trim();
    if (!text) return null;
    const now = Date.now();
    for (const [key, time] of recentMessages) if (now - time > 10000) recentMessages.delete(key);
    const dedupeKey = `${type}:${text}`;
    if (now - (recentMessages.get(dedupeKey) || 0) < (options.dedupeMs ?? 1400)) return null;
    recentMessages.set(dedupeKey, now);

    const region = ensureToastRegion();
    const toast = document.createElement('div');
    const normalizedType = notificationType(type);
    const toastId = `fox-toast-${++toastSequence}`;
    toast.id = toastId;
    toast.className = `fox-toast fox-toast--${normalizedType}`;
    toast.dataset.toastType = normalizedType;
    toast.setAttribute('role', normalizedType === 'error' ? 'alert' : 'status');
    toast.innerHTML = '<span class="fox-toast-mark" aria-hidden="true"></span><span class="fox-toast-message"></span><button type="button" class="fox-toast-close" aria-label="关闭通知">×</button>';
    toast.querySelector('.fox-toast-message').textContent = text;

    const remove = () => {
      toast.classList.add('is-leaving');
      setTimeout(() => toast.remove(), 180);
    };
    toast.querySelector('.fox-toast-close').addEventListener('click', remove);
    region.appendChild(toast);
    while (region.children.length > 4) region.firstElementChild.remove();
    requestAnimationFrame(() => toast.classList.add('is-visible'));

    const duration = options.duration ?? (normalizedType === 'error' ? 7000 : 4200);
    if (duration > 0) setTimeout(remove, duration);
    return toastId;
  }

  function setBusy(target, busy, label = '') {
    const element = elementOf(target);
    if (!element) return false;
    if (busy) {
      if (!busyStates.has(element)) {
        busyStates.set(element, {
          disabled: Boolean(element.disabled),
          html: element.innerHTML,
        });
      }
      element.disabled = true;
      element.setAttribute('aria-busy', 'true');
      element.classList.add('is-busy');
      if (label) element.textContent = label;
      return true;
    }

    const previous = busyStates.get(element);
    if (previous) {
      element.disabled = previous.disabled;
      element.innerHTML = previous.html;
      busyStates.delete(element);
    } else {
      element.disabled = false;
    }
    element.removeAttribute('aria-busy');
    element.classList.remove('is-busy');
    return true;
  }

  function registerDialog(target, config = {}) {
    const element = elementOf(target);
    if (!element?.id) return false;
    dialogs.set(element.id, { ...config });
    return true;
  }

  function focusableElements(dialog) {
    return [...dialog.querySelectorAll(focusableSelector)].filter(element => {
      const style = getComputedStyle(element);
      return !element.hidden && style.display !== 'none' && style.visibility !== 'hidden';
    });
  }

  function openDialog(target, options = {}) {
    const dialog = elementOf(target);
    if (!dialog) return false;
    const config = { ...(dialogs.get(dialog.id) || {}), ...options };
    if (dialog.hidden) dialogOpeners.set(dialog, document.activeElement);
    dialog.hidden = false;
    dialog.setAttribute('data-fox-dialog-open', 'true');
    const existingIndex = dialogStack.indexOf(dialog);
    if (existingIndex >= 0) dialogStack.splice(existingIndex, 1);
    dialogStack.push(dialog);
    window.FoxMotion?.play('panel', dialog.firstElementChild, dialog);

    requestAnimationFrame(() => {
      if (dialog.hidden || topDialog() !== dialog) return;
      const requested = elementOf(config.initialFocus);
      const fallback = focusableElements(dialog)[0] || dialog;
      if (!dialog.hasAttribute('tabindex') && fallback === dialog) dialog.tabIndex = -1;
      (requested && dialog.contains(requested) ? requested : fallback)?.focus?.();
    });
    return true;
  }

  function closeDialog(target, options = {}) {
    const dialog = elementOf(target);
    if (!dialog) return false;
    window.FoxMotion?.cancel(dialog);
    dialog.hidden = true;
    dialog.removeAttribute('data-fox-dialog-open');
    const stackIndex = dialogStack.lastIndexOf(dialog);
    if (stackIndex >= 0) dialogStack.splice(stackIndex, 1);
    if (options.restoreFocus !== false) {
      const opener = dialogOpeners.get(dialog);
      if (opener?.isConnected) requestAnimationFrame(() => opener.focus?.());
    }
    dialogOpeners.delete(dialog);
    return true;
  }

  function topDialog() {
    while (dialogStack.length && dialogStack.at(-1).hidden) dialogStack.pop();
    return dialogStack.at(-1) || null;
  }

  function requestDialogClose(dialog) {
    const config = dialogs.get(dialog.id) || {};
    if (typeof config.onRequestClose === 'function') config.onRequestClose();
    else closeDialog(dialog);
  }

  function trapDialogFocus(event, dialog) {
    const items = focusableElements(dialog);
    if (!items.length) {
      event.preventDefault();
      dialog.focus();
      return;
    }
    const first = items[0];
    const last = items.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function registerCommand(command, config = {}) {
    const value = typeof command === 'string' ? { id:command, ...config } : command;
    if (!value?.id || !value.label || typeof value.run !== 'function') return false;
    commands.set(value.id, {
      group:'操作',
      description:'',
      keywords:[],
      shortcut:'',
      ...value,
    });
    return true;
  }

  function commandEnabled(command) {
    return typeof command.isEnabled === 'function' ? Boolean(command.isEnabled()) : command.isEnabled !== false;
  }

  function searchCommands(query = '') {
    const normalized = query.trim().toLowerCase();
    return [...commands.values()].filter(command => {
      if (!commandEnabled(command)) return false;
      const haystack = [command.label, command.description, command.group, ...(command.keywords || [])].join(' ').toLowerCase();
      return !normalized || haystack.includes(normalized);
    });
  }

  async function runCommand(id, context = {}) {
    const command = commands.get(id);
    if (!command || !commandEnabled(command)) return false;
    try {
      await command.run(context);
      return true;
    } catch (error) {
      notify(`操作失败：${error?.message || error}`, 'error');
      return false;
    }
  }

  function handleGlobalKeydown(event) {
    const dialog = topDialog();
    if (!dialog) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopImmediatePropagation();
      requestDialogClose(dialog);
      return;
    }
    if (event.key === 'Tab') trapDialogFocus(event, dialog);
  }

  function handleBackdrop(event) {
    const dialog = event.target.closest?.('[role="dialog"][data-fox-dialog-open="true"]');
    if (dialog && event.target === dialog) requestDialogClose(dialog);
  }

  function initialize() {
    ensureToastRegion();
    if (initialized) return;
    initialized = true;
    document.addEventListener('keydown', handleGlobalKeydown, true);
    document.addEventListener('pointerdown', handleBackdrop);
  }

  window.FoxInteraction = {
    initialize,
    notify,
    setBusy,
    registerDialog,
    openDialog,
    closeDialog,
    registerCommand,
    searchCommands,
    runCommand,
  };
})();
