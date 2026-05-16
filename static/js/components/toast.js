/**
 * Toast 消息提示
 */
const Toast = (() => {
  let container = null;

  function ensureContainer() {
    if (!container) {
      container = document.getElementById('toast-container');
    }
  }

  function show(message, type = 'info', duration = 3000) {
    ensureContainer();
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = message;
    container.appendChild(el);
    requestAnimationFrame(() => el.classList.add('toast--visible'));
    setTimeout(() => {
      el.classList.remove('toast--visible');
      setTimeout(() => el.remove(), 300);
    }, duration);
  }

  return { show };
})();
