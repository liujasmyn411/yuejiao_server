/**
 * 心理预警页 — 列表 + 新增
 */
const PsychAlertsPage = (() => {
  let currentFilter = '';

  function render() {
    return `
      <div class="page-header flex-between">
        <div>
          <div class="filter-tabs" id="alert-filter-tabs">
            <button class="filter-tab filter-tab--active" data-level="">全部</button>
            <button class="filter-tab" data-level="high">高风险</button>
            <button class="filter-tab" data-level="medium">中风险</button>
            <button class="filter-tab" data-level="low">低风险</button>
            <button class="filter-tab" data-level="none">无风险</button>
          </div>
        </div>
        <button class="btn btn-primary" id="btn-add-alert">+ 新增预警</button>
      </div>
      <div id="alert-table" class="table-container mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    document.getElementById('btn-add-alert').onclick = openCreateModal;
    document.querySelectorAll('#alert-filter-tabs .filter-tab').forEach(tab => {
      tab.onclick = () => {
        document.querySelectorAll('#alert-filter-tabs .filter-tab').forEach(t => t.classList.remove('filter-tab--active'));
        tab.classList.add('filter-tab--active');
        currentFilter = tab.dataset.level;
        load();
      };
    });
    load();
  }

  async function load() {
    const container = document.getElementById('alert-table');
    try {
      const url = currentFilter ? `/api/student/psych-alert?risk_level=${currentFilter}` : '/api/student/psych-alert';
      const data = await API.get(url);
      const alerts = data.alerts || [];
      if (!alerts.length) {
        container.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">🧠</div><h3>暂无心理预警</h3><p>点击右上角"新增预警"添加</p></div>';
        return;
      }
      container.innerHTML = `
        <table class="table">
          <thead><tr><th>ID</th><th>学生ID</th><th>触发原因</th><th>风险等级</th><th>来源</th><th>状态</th><th>处理内容</th></tr></thead>
          <tbody>
            ${alerts.map(a => `
              <tr>
                <td>${a.id}</td>
                <td>${a.student_id}</td>
                <td>${esc(a.trigger_reason || '-')}</td>
                <td>${riskTag(a.risk_level)}</td>
                <td>${esc(a.alert_source || '-')}</td>
                <td>${statusTag(a.status)}</td>
                <td style="max-width:200px">${esc(a.handle_content || '-')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function openCreateModal() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    Modal.show({
      title: '新增心理预警',
      body: `
        <div class="form-grid">
          <div class="form-group">
            <label>学生ID <span class="text-error">*</span></label>
            <input id="alert-student-id" class="input" type="number" value="${user.user_type === 'STUDENT' ? user.id : ''}" placeholder="必填">
          </div>
          <div class="form-group">
            <label>风险等级 <span class="text-error">*</span></label>
            <select id="alert-level" class="select">
              <option value="">请选择</option>
              <option value="high">高风险</option>
              <option value="medium" selected>中风险</option>
              <option value="low">低风险</option>
              <option value="none">无风险</option>
            </select>
          </div>
          <div class="form-group">
            <label>预警来源</label>
            <select id="alert-source" class="select">
              <option value="聊天对话" selected>聊天对话</option>
              <option value="人工观察">人工观察</option>
              <option value="测评问卷">测评问卷</option>
              <option value="他人反馈">他人反馈</option>
            </select>
          </div>
          <div class="form-group" style="grid-column:span 2">
            <label>触发原因</label>
            <textarea id="alert-reason" class="textarea" rows="3" placeholder="描述触发预警的原因..."></textarea>
          </div>
        </div>
      `,
      confirmText: '提交',
      onConfirm: async () => {
        const studentId = parseInt(document.getElementById('alert-student-id').value);
        const level = document.getElementById('alert-level').value;
        if (!studentId) { Toast.show('请输入学生ID', 'warning'); return; }
        if (!level) { Toast.show('请选择风险等级', 'warning'); return; }
        try {
          await API.post('/api/student/psych-alert', {
            student_id: studentId,
            risk_level: level,
            trigger_reason: document.getElementById('alert-reason').value,
            alert_source: document.getElementById('alert-source').value,
          });
          Toast.show('预警已提交', 'success');
          load();
        } catch (e) { Toast.show(e.message, 'error'); }
      },
    });
  }

  function riskTag(level) {
    const map = { high: 'tag-red', medium: 'tag-orange', low: 'tag-blue', none: 'tag-green' };
    const label = { high: '高风险', medium: '中风险', low: '低风险', none: '无风险' };
    return `<span class="tag ${map[level] || ''}">${label[level] || esc(level)}</span>`;
  }

  function statusTag(s) {
    const map = { '待处理': 'tag-orange', '处理中': 'tag-blue', '已处理': 'tag-green' };
    return `<span class="tag ${map[s] || 'tag-blue'}">${esc(s)}</span>`;
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
