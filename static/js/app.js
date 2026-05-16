/**
 * 应用入口 — 初始化所有组件、注册路由、启动
 */
const App = (() => {
  function init() {
    // 初始化聊天浮窗
    ChatWidget.init();

    // 注册所有路由
    // 登录（无需认证）
    Router.register('/login', LoginPage.render, {
      requireAuth: false,
      onMount: LoginPage.onMount,
    });

    // 仪表盘
    Router.register('/dashboard', DashboardPage.render, {
      requireAuth: true,
      onMount: DashboardPage.onMount,
    });

    // 占位页面（后续逐一实现）
    const pages = [
      '/events', '/projects', '/profile-match', '/parse-file',
      '/leads', '/reports', '/scores', '/employees', '/approvals', '/org-chart',
      '/academic', '/study-abroad', '/leave', '/feedback', '/notifications',
    ];
    pages.forEach(path => {
      Router.register(path, () => {
        const titles = {
          '/events': '活动讲座', '/projects': '课程项目', '/profile-match': '画像研判',
          '/parse-file': '文件解析', '/leads': 'CRM客户管理', '/reports': '员工日报',
          '/scores': '成绩管理', '/employees': '员工通讯录', '/approvals': '审批管理',
          '/org-chart': '组织架构', '/academic': '教务DDL', '/study-abroad': '留学进度',
          '/leave': '请假申请', '/feedback': '反馈工单', '/notifications': '通知中心',
        };
        return `<div class="page-placeholder">
          <div class="placeholder-icon">🚧</div>
          <h3>${titles[path]}</h3>
          <p>此页面即将实现...</p>
        </div>`;
      }, { requireAuth: true });
    });

    // 检查登录态，渲染初始页面
    const token = localStorage.getItem('access_token');
    if (token) {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      Sidebar.render();
      Topbar.render('/dashboard');
      Topbar.updateUnread();
      const agentMap = { STUDENT: 'student', EMPLOYEE: 'enterprise', ADMIN: 'enterprise' };
      ChatWidget.setAgent(agentMap[user.user_type] || 'customer', user.id);
    }

    Router.init();
  }

  function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    Sidebar.render();
    Topbar.render('/login');
    Router.navigate('/login');
    Toast.show('已退出登录');
  }

  return { init, logout };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
