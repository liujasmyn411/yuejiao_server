/**
 * 侧边导航栏 — 按用户角色动态展示菜单
 */
const Sidebar = (() => {
  // 各角色菜单配置
  const menuConfig = {
    ADMIN: [
      { icon: '📊', label: '仪表盘', path: '/dashboard', roles: ['ADMIN', 'EMPLOYEE', 'STUDENT'] },
      { label: '— 客服 —', roles: ['ADMIN', 'EMPLOYEE'], type: 'label' },
      { icon: '📅', label: '活动讲座', path: '/events', roles: ['ADMIN', 'EMPLOYEE'] },
      { icon: '📚', label: '课程项目', path: '/projects', roles: ['ADMIN', 'EMPLOYEE'] },
      { icon: '🎯', label: '画像研判', path: '/profile-match', roles: ['ADMIN', 'EMPLOYEE'] },
      { icon: '📎', label: '文件解析', path: '/parse-file', roles: ['ADMIN', 'EMPLOYEE'] },
      { label: '— 企业 —', roles: ['ADMIN', 'EMPLOYEE'], type: 'label' },
      { icon: '👥', label: 'CRM客户', path: '/leads', roles: ['ADMIN', 'EMPLOYEE'] },
      { icon: '📝', label: '员工日报', path: '/reports', roles: ['ADMIN', 'EMPLOYEE'] },
      { icon: '📈', label: '成绩管理', path: '/scores', roles: ['ADMIN', 'EMPLOYEE'] },
      { icon: '👤', label: '员工通讯录', path: '/employees', roles: ['ADMIN', 'EMPLOYEE'] },
      { icon: '✅', label: '审批管理', path: '/approvals', roles: ['ADMIN', 'EMPLOYEE'] },
      { icon: '🏢', label: '组织架构', path: '/org-chart', roles: ['ADMIN', 'EMPLOYEE'] },
      { icon: '📊', label: '报表中心', path: '/reports-center', roles: ['ADMIN', 'EMPLOYEE'] },

      { label: '— 学生 —', roles: ['ADMIN', 'STUDENT'], type: 'label' },
      { icon: '📋', label: '教务DDL', path: '/academic', roles: ['ADMIN', 'STUDENT'] },
      { icon: '🎓', label: '留学进度', path: '/study-abroad', roles: ['ADMIN', 'STUDENT'] },
      { icon: '🏖', label: '请假申请', path: '/leave', roles: ['ADMIN', 'STUDENT'] },
      { icon: '💬', label: '反馈工单', path: '/feedback', roles: ['ADMIN', 'STUDENT'] },
      { icon: '🔔', label: '通知中心', path: '/notifications', roles: ['ADMIN', 'STUDENT'] },
      { icon: '🧠', label: '心理预警', path: '/psych-alert', roles: ['ADMIN', 'EMPLOYEE'] },
      { icon: '🎓', label: '学生信息', path: '/student-info', roles: ['ADMIN', 'STUDENT'] },
    ],
    EMPLOYEE: [], // 复用 ADMIN 的（通过 roles 字段控制）
    STUDENT: [],
  };

  function getUser() {
    try { return JSON.parse(localStorage.getItem('user') || '{}'); } catch (e) { return {}; }
  }

  function getMenuItems() {
    const user = getUser();
    const userType = user.user_type || 'STUDENT';
    // 所有菜单项（以 ADMIN 配置为全集）
    const allItems = menuConfig.ADMIN;
    return allItems.filter(item => {
      if (!item.roles) return true;
      return item.roles.includes(userType);
    });
  }

  function render() {
    const items = getMenuItems();
    const user = getUser();
    const html = `
      <div class="sidebar__brand">
        <span class="sidebar__logo">🎓</span>
        <span class="sidebar__title">粤教服务</span>
      </div>
      <div class="sidebar__user">
        <div class="sidebar__avatar">${(user.real_name || '?')[0]}</div>
        <div>
          <div class="sidebar__username">${user.real_name || '未登录'}</div>
          <div class="sidebar__role">${roleLabel(user.user_type)}</div>
        </div>
      </div>
      <nav class="sidebar__nav">
        ${items.map(item => {
          if (item.type === 'label') {
            return `<div class="sidebar__label">${item.label}</div>`;
          }
          return `
            <a class="sidebar__item" data-path="${item.path}" href="#${item.path}">
              <span class="sidebar__icon">${item.icon}</span>
              <span>${item.label}</span>
            </a>
          `;
        }).join('')}
      </nav>
      <div class="sidebar__footer">
        <a class="sidebar__item sidebar__item--logout" href="#" onclick="App.logout()">
          <span class="sidebar__icon">🚪</span>
          <span>退出登录</span>
        </a>
      </div>
    `;

    document.getElementById('sidebar').innerHTML = html;
  }

  function setActive(path) {
    document.querySelectorAll('.sidebar__item').forEach(el => el.classList.remove('sidebar__item--active'));
    const active = document.querySelector(`.sidebar__item[data-path="${path}"]`);
    if (active) active.classList.add('sidebar__item--active');
  }

  function roleLabel(type) {
    const map = { ADMIN: '管理员', EMPLOYEE: '员工', STUDENT: '学生' };
    return map[type] || type;
  }

  return { render, setActive };
})();
