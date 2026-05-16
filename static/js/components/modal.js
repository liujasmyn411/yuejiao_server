/**
 * 通用弹窗组件
 * Modal.show({ title, body, onConfirm, confirmText, cancelText, size })
 */
const Modal = (() => {
  function show(opts = {}) {
    const {
      title = '提示',
      body = '',
      onConfirm,
      onCancel,
      confirmText = '确定',
      cancelText = '取消',
      size = '',
      showCancel = true,
    } = opts;

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal ${size}">
        <div class="modal__header">
          <span>${title}</span>
          <button class="btn-icon modal__close">✕</button>
        </div>
        <div class="modal__body">${body}</div>
        <div class="modal__footer">
          ${showCancel ? `<button class="btn modal__cancel">${cancelText}</button>` : ''}
          <button class="btn btn-primary modal__confirm">${confirmText}</button>
        </div>
      </div>
    `;

    overlay.querySelector('.modal__close').onclick = close;
    overlay.querySelector('.modal__cancel') && (overlay.querySelector('.modal__cancel').onclick = close);
    overlay.querySelector('.modal__confirm').onclick = () => {
      if (onConfirm) onConfirm();
      close();
    };
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

    function close() {
      overlay.classList.add('modal-overlay--closing');
      setTimeout(() => overlay.remove(), 200);
      if (onCancel) onCancel();
    }

    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('modal-overlay--visible'));
  }

  function hide() {
    const overlay = document.querySelector('.modal-overlay');
    if (overlay) {
      overlay.classList.remove('modal-overlay--visible');
      setTimeout(() => overlay.remove(), 200);
    }
  }

  return { show, hide };
})();
