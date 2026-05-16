/**
 * 仪表盘页 — 按角色展示不同统计卡片
 */
const DashboardPage = (() => {
  function render() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const userType = user.user_type;

    if (userType === 'STUDENT') {
      return renderStudentDashboard(user);
    }
    return renderEmployeeDashboard(user);
  }

  function renderEmployeeDashboard(user) {
    return `
      <div class="dashboard">
        <div class="dashboard__greeting">
          <h3>👋 欢迎回来，${user.real_name}</h3>
          <p>以下是今日工作概览</p>
        </div>
        <div id="stats-cards" class="stats-grid">
          <div class="stat-card stat-card--blue">
            <div class="stat-card__icon">👥</div>
            <div class="stat-card__value" id="stat-leads">-</div>
            <div class="stat-card__label">意向客户总数</div>
          </div>
          <div class="stat-card stat-card--green">
            <div class="stat-card__icon">📝</div>
            <div class="stat-card__value" id="stat-reports">-</div>
            <div class="stat-card__label">今日日报数</div>
          </div>
          <div class="stat-card stat-card--orange">
            <div class="stat-card__icon">✅</div>
            <div class="stat-card__value" id="stat-pending">-</div>
            <div class="stat-card__label">待审批事项</div>
          </div>
          <div class="stat-card stat-card--purple">
            <div class="stat-card__icon">📅</div>
            <div class="stat-card__value" id="stat-events">-</div>
            <div class="stat-card__label">进行中活动</div>
          </div>
        </div>
        <div class="dashboard__section">
          <h4 class="section-title">快捷操作</h4>
          <div class="quick-actions">
            <a href="#/leads" class="quick-action">
              <span class="quick-action__icon">➕</span>
              <span>新增客户</span>
            </a>
            <a href="#/reports" class="quick-action">
              <span class="quick-action__icon">📝</span>
              <span>写日报</span>
            </a>
            <a href="#/events" class="quick-action">
              <span class="quick-action__icon">📅</span>
              <span>查看活动</span>
            </a>
            <a href="#/org-chart" class="quick-action">
              <span class="quick-action__icon">🏢</span>
              <span>组织架构</span>
            </a>
          </div>
        </div>
      </div>
    `;
  }

  function renderStudentDashboard(user) {
    return `
      <div class="dashboard">
        <div class="dashboard__greeting">
          <h3>👋 你好，${user.real_name}</h3>
          <p>以下是你的学业概览</p>
        </div>
        <div id="stats-cards" class="stats-grid">
          <div class="stat-card stat-card--blue">
            <div class="stat-card__icon">📋</div>
            <div class="stat-card__value" id="stat-academic">-</div>
            <div class="stat-card__label">待完成DDL</div>
          </div>
          <div class="stat-card stat-card--green">
            <div class="stat-card__icon">🎓</div>
            <div class="stat-card__value" id="stat-progress">-</div>
            <div class="stat-card__label">留学当前阶段</div>
          </div>
          <div class="stat-card stat-card--orange">
            <div class="stat-card__icon">🔔</div>
            <div class="stat-card__value" id="stat-notif">-</div>
            <div class="stat-card__label">未读通知</div>
          </div>
          <div class="stat-card stat-card--purple">
            <div class="stat-card__icon">📊</div>
            <div class="stat-card__value" id="stat-scores">-</div>
            <div class="stat-card__label">已出成绩</div>
          </div>
        </div>
        <div class="dashboard__section">
          <h4 class="section-title">快捷操作</h4>
          <div class="quick-actions">
            <a href="#/academic" class="quick-action">
              <span class="quick-action__icon">📋</span>
              <span>查看DDL</span>
            </a>
            <a href="#/study-abroad" class="quick-action">
              <span class="quick-action__icon">🎓</span>
              <span>留学进度</span>
            </a>
            <a href="#/leave" class="quick-action">
              <span class="quick-action__icon">🏖</span>
              <span>请假申请</span>
            </a>
            <a href="#/notifications" class="quick-action">
              <span class="quick-action__icon">🔔</span>
              <span>通知中心</span>
            </a>
          </div>
        </div>
      </div>
    `;
  }

  async function onMount() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    try {
      if (user.user_type === 'STUDENT') {
        await loadStudentStats(user.id);
      } else {
        const data = await API.get('/api/enterprise/dashboard');
        if (data) {
          setValue('stat-leads', data.lead_count || data.total_leads || '0');
          setValue('stat-reports', data.report_count || data.today_reports || '0');
          setValue('stat-pending', data.pending_count || data.pending_approvals || '0');
          setValue('stat-events', data.event_count || data.active_events || '0');
        }
      }
    } catch (e) {
      document.querySelectorAll('.stat-card__value').forEach(el => el.textContent = '--');
    }
  }

  async function loadStudentStats(studentId) {
    try {
      const [academicData, progressData, notifData] = await Promise.all([
        API.get(`/api/student/academic?student_id=${studentId}`),
        API.get(`/api/student/study-abroad/current?student_id=${studentId}`),
        API.get(`/api/student/notification/unread-count?recipient_id=${studentId}`),
      ]);
      const academics = academicData.academics || [];
      const pending = academics.filter(a => a.ddl_status === '未完成').length;
      setValue('stat-academic', pending);
      setValue('stat-progress', progressData.stage || '暂无');
      setValue('stat-notif', notifData.unread_count || 0);
      try {
        const scoreData = await API.get(`/api/enterprise/score?student_id=${studentId}`);
        setValue('stat-scores', (scoreData.scores || []).length);
      } catch (e) { setValue('stat-scores', '--'); }
    } catch (e) {
      document.querySelectorAll('.stat-card__value').forEach(el => el.textContent = '--');
    }
  }

  function setValue(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  return { render, onMount };
})();
