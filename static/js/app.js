/**
 * 应用入口 — 初始化所有组件、注册路由、启动
 */
const App = (() => {
  function init() {
    ChatWidget.init();

    Router.register('/login', LoginPage.render, { requireAuth: false, onMount: LoginPage.onMount });
    Router.register('/dashboard', DashboardPage.render, { requireAuth: true, onMount: DashboardPage.onMount });
    Router.register('/leads', LeadsPage.render, { requireAuth: true, onMount: LeadsPage.onMount });
    Router.register('/academic', AcademicPage.render, { requireAuth: true, onMount: AcademicPage.onMount });
    Router.register('/events', EventsPage.render, { requireAuth: true, onMount: EventsPage.onMount });
    Router.register('/projects', ProjectsPage.render, { requireAuth: true, onMount: ProjectsPage.onMount });
    Router.register('/profile-match', ProfileMatchPage.render, { requireAuth: true, onMount: ProfileMatchPage.onMount });
    Router.register('/parse-file', ParseFilePage.render, { requireAuth: true, onMount: ParseFilePage.onMount });
    Router.register('/reports', ReportsPage.render, { requireAuth: true, onMount: ReportsPage.onMount });
    Router.register('/scores', ScoresPage.render, { requireAuth: true, onMount: ScoresPage.onMount });
    Router.register('/employees', EmployeesPage.render, { requireAuth: true, onMount: EmployeesPage.onMount });
    Router.register('/approvals', ApprovalsPage.render, { requireAuth: true, onMount: ApprovalsPage.onMount });
    Router.register('/org-chart', OrgChartPage.render, { requireAuth: true, onMount: OrgChartPage.onMount });
    Router.register('/study-abroad', StudyAbroadPage.render, { requireAuth: true, onMount: StudyAbroadPage.onMount });
    Router.register('/leave', LeavePage.render, { requireAuth: true, onMount: LeavePage.onMount });
    Router.register('/feedback', FeedbackPage.render, { requireAuth: true, onMount: FeedbackPage.onMount });
    Router.register('/notifications', NotificationsPage.render, { requireAuth: true, onMount: NotificationsPage.onMount });

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
