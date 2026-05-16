/**
 * 顶栏组件 — 面包屑 + 通知 + 用户信息
 */
const Topbar = (() => {
  function render(path = '') {
    const user = getUser();
    const title = pageTitle(path);
    document.getElementById('topbar').innerHTML = `
      <div class="topbar__left">
        <h2 class="topbar__title">${title}</h2>
      </div>
      <div class="topbar__right">
        <button class="btn-icon topbar__notif" onclick="Router.navigate('/notifications')" title="通知中心">
          🔔 <span id="unread-badge" class="badge hidden">0</span>
        </button>
        <div class="topbar__user">
          <span class="topbar__avatar">${(user.real_name || '?')[0]}</span>
          <span class="topbar__name">${user.real_name || ''}</span>
        </div>
      </div>
    `;
  }

  function pageTitle(path) {
    const titles = {
      '/dashboard': '仪表盘', '/events': '活动讲座', '/projects': '课程项目',
      '/profile-match': '画像研判', '/parse-file': '文件解析',
      '/leads': 'CRM客户管理', '/reports': '员工日报', '/scores': '成绩管理',
      '/employees': '员工通讯录', '/approvals': '审批管理', '/org-chart': '组织架构',
      '/academic': '教务DDL', '/study-abroad': '留学进度', '/leave': '请假申请',
      '/feedback': '反馈工单', '/notifications': '通知中心', '/login': '登录',
    };
    return titles[path] || '粤教服务';
  }

  function getUser() {
    try { return JSON.parse(localStorage.getItem('user') || '{}'); } catch (e) { return {}; }
  }

  async function updateUnread() {
    const user = getUser();
    if (!user.id) return;
    try {
      const data = await API.get(`/api/student/notification/unread-count?recipient_id=${user.id}`);
      const badge = document.getElementById('unread-badge');
      if (!badge) return;
      const count = data.unread_count || 0;
      if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.remove('hidden');
      } else {
        badge.classList.add('hidden');
      }
    } catch (e) { /* 非学生类型可能会 403，忽略 */ }
  }

  return { render, updateUnread };
})();
