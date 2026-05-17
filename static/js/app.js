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
    Router.register('/psych-alert', PsychAlertsPage.render, { requireAuth: true, onMount: PsychAlertsPage.onMount });
    Router.register('/reports-center', ReportsCenterPage.render, { requireAuth: true, onMount: ReportsCenterPage.onMount });
    Router.register('/student-info', StudentInfoPage.render, { requireAuth: true, onMount: StudentInfoPage.onMount });
    Router.register('/nl2sql', Nl2sqlPage.render, { requireAuth: true, onMount: Nl2sqlPage.onMount });

    const token = localStorage.getItem('access_token');
    const initialPath = location.hash.slice(1) || (token ? '/dashboard' : '/login');

    if (token) {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      Sidebar.render();
      Topbar.render(initialPath);
      Topbar.updateUnread();
      ChatWidget.setAgent('unified', user.id);
    }

    Router.init();
  }

  function logout() {
    // 保存当前会话到历史
    ChatWidget.saveCurrentSession();
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    ChatWidget.setAgent(null, null);
    Sidebar.render();
    Topbar.render('/login');
    Router.navigate('/login');
    Toast.show('已退出登录');
  }

  return { init, logout };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
