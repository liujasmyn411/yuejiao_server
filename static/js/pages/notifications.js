/**
 * 通知中心页 — 列表 + 已读/全部已读
 */
const NotificationsPage = (() => {
  function render() {
    return `
      <div class="page-header flex-between">
        <h3 style="margin:0">🔔 通知中心</h3>
        <button class="btn btn-primary" id="btn-read-all">标记全部已读</button>
      </div>
      <div id="notif-list" class="mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    document.getElementById('btn-read-all').onclick = () => markAllRead(user.id);
    await load(user.id);
    Topbar.updateUnread();
  }

  async function load(userId) {
    const container = document.getElementById('notif-list');
    try {
      const data = await API.get(`/api/student/notification?recipient_id=${userId}`);
      const notifs = data.notifications || [];
      if (!notifs.length) {
        container.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">🔔</div><h3>暂无通知</h3></div>';
        return;
      }
      container.innerHTML = notifs.map(n => `
        <div class="card notif-card ${n.is_read ? '' : 'notif-card--unread'} mb-16">
          <div class="flex-between">
            <div class="flex-center gap-8">
              ${n.is_read ? '' : '<span class="notif-dot"></span>'}
              <h4>${esc(n.title)}</h4>
              <span class="tag tag-blue">${esc(n.notification_type)}</span>
            </div>
            <div class="flex-center gap-8">
              <small class="text-muted">${(n.create_time || '').slice(0,16).replace('T',' ')}</small>
              ${n.is_read ? '' : `<button class="btn btn-sm btn-read" data-id="${n.id}">标记已读</button>`}
            </div>
          </div>
          <p class="text-muted mt-16">${esc(n.content)}</p>
        </div>
      `).join('');

      container.querySelectorAll('.btn-read').forEach(btn => {
        btn.onclick = async () => {
          try {
            await API.put(`/api/student/notification/${btn.dataset.id}/read?recipient_id=${userId}`, {});
            Toast.show('已标记为已读', 'success');
            load(userId);
            Topbar.updateUnread();
          } catch (e) { Toast.show(e.message, 'error'); }
        };
      });
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  async function markAllRead(userId) {
    try {
      await API.put(`/api/student/notification/read-all?recipient_id=${userId}`, {});
      Toast.show('全部已读', 'success');
      load(userId);
      Topbar.updateUnread();
    } catch (e) { Toast.show(e.message, 'error'); }
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
