/**
 * Hash 路由 — 极简 SPA 导航
 * 页面只需注册一个渲染函数，路由切换时自动调用
 */
const Router = (() => {
  const pages = {};
  let currentPage = null;
  let navigating = false;

  function register(path, renderFn, meta = {}) {
    pages[path] = { render: renderFn, meta };
  }

  async function navigate(path) {
    // 防止重复导航到同一页面
    if (navigating) return;
    if (currentPage === path) return;

    const page = pages[path];
    if (!page) {
      // 页面未注册，跳转到登录页
      redirectTo('/login');
      return;
    }

    // 需要登录的页面
    if (page.meta.requireAuth && !API.getToken()) {
      redirectTo('/login');
      return;
    }

    // 角色限制
    if (page.meta.roles && page.meta.roles.length > 0) {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      if (!page.meta.roles.includes(user.user_type)) {
        redirectTo('/dashboard');
        return;
      }
    }

    navigating = true;
    currentPage = path;

    // 同步 URL hash（不触发 hashchange 的 navigate 调用）
    const hashPath = '#' + path;
    if (location.hash !== hashPath) {
      location.hash = hashPath;
    }

    const content = document.getElementById('content');
    if (!content) { navigating = false; return; }

    // 登录页隐藏 sidebar/topbar，其他页面显示
    const sidebar = document.getElementById('sidebar');
    const topbar = document.getElementById('topbar');
    const mainArea = document.querySelector('.main-area');
    if (path === '/login') {
      if (sidebar) sidebar.style.display = 'none';
      if (topbar) topbar.style.display = 'none';
      if (mainArea) mainArea.style.marginLeft = '0';
    } else {
      if (sidebar) sidebar.style.display = '';
      if (topbar) topbar.style.display = '';
      if (mainArea) mainArea.style.marginLeft = '';
    }

    content.innerHTML = '<div class="page-loading">加载中...</div>';
    try {
      const html = await page.render();
      content.innerHTML = html;
      if (typeof page.meta.onMount === 'function') {
        page.meta.onMount();
      }
    } catch (err) {
      content.innerHTML = `<div class="page-error">页面加载失败: ${err.message}</div>`;
      console.error(err);
    }
    if (path !== '/login') {
      Sidebar.setActive(path);
    }
    // 更新顶栏标题
    const titleEl = document.querySelector('.topbar__title');
    if (titleEl) {
      const titles = {
        '/dashboard': '仪表盘', '/events': '活动讲座', '/projects': '课程项目',
        '/profile-match': '画像研判', '/parse-file': '文件解析',
        '/leads': 'CRM客户管理', '/reports': '员工日报', '/scores': '成绩管理',
        '/employees': '员工通讯录', '/approvals': '审批管理', '/org-chart': '组织架构',
        '/academic': '教务DDL', '/study-abroad': '留学进度', '/leave': '请假申请',
        '/feedback': '反馈工单', '/notifications': '通知中心',
        '/psych-alert': '心理预警', '/reports-center': '报表中心',
        '/student-info': '学生信息',
        '/login': '登录',
      };
      titleEl.textContent = titles[path] || '粤教服务';
    }
    navigating = false;
  }

  function redirectTo(path) {
    location.hash = '#' + path;
  }

  function init() {
    window.addEventListener('hashchange', () => {
      const path = location.hash.slice(1) || '/login';
      navigate(path);
    });

    // 初始路由：已有 token 则默认去 dashboard，否则去 login
    const path = location.hash.slice(1);
    if (path) {
      navigate(path);
    } else if (API.getToken()) {
      navigate('/dashboard');
    } else {
      navigate('/login');
    }
  }

  return { register, navigate, init, pages };
})();
