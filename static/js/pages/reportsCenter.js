/**
 * 报表中心页 — Tab 切换 6 种报表视图
 */
const ReportsCenterPage = (() => {
  let currentTab = 'dashboard';

  const tabs = [
    { key: 'dashboard', label: '管理仪表盘' },
    { key: 'customer', label: '客户分析' },
    { key: 'daily', label: '日报汇总' },
    { key: 'weekly', label: '周报汇总' },
    { key: 'psych', label: '心理周报' },
    { key: 'complaint', label: '投诉周报' },
  ];

  function render() {
    return `
      <div class="page-header">
        <h3 style="margin:0">📊 报表中心</h3>
      </div>
      <div class="filter-tabs mt-16" id="report-tabs">
        ${tabs.map(t => `
          <button class="filter-tab ${t.key === currentTab ? 'filter-tab--active' : ''}" data-tab="${t.key}">${t.label}</button>
        `).join('')}
      </div>
      <div id="report-content" class="mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  function onMount() {
    document.querySelectorAll('#report-tabs .filter-tab').forEach(tab => {
      tab.onclick = () => {
        document.querySelectorAll('#report-tabs .filter-tab').forEach(t => t.classList.remove('filter-tab--active'));
        tab.classList.add('filter-tab--active');
        currentTab = tab.dataset.tab;
        loadTab();
      };
    });
    loadTab();
  }

  async function loadTab() {
    const container = document.getElementById('report-content');
    container.innerHTML = '<div class="page-loading">加载中...</div>';

    try {
      switch (currentTab) {
        case 'dashboard': await loadDashboard(container); break;
        case 'customer': await loadCustomer(container); break;
        case 'daily': await loadDaily(container); break;
        case 'weekly': await loadWeekly(container); break;
        case 'psych': await loadPsych(container); break;
        case 'complaint': await loadComplaint(container); break;
      }
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  async function loadDashboard(container) {
    const data = await API.get('/api/reports/dashboard');
    container.innerHTML = renderStatCards(data);
  }

  async function loadCustomer(container) {
    const data = await API.get('/api/reports/customer');
    container.innerHTML = renderReportData('客户经营分析报告', data);
  }

  async function loadDaily(container) {
    const data = await API.get('/api/reports/daily');
    container.innerHTML = `
      <div class="card mb-16">
        <div class="form-grid">
          <div class="form-group">
            <label>日期（可选）</label>
            <input id="rc-daily-date" class="input" type="date">
          </div>
          <div class="form-group">
            <label>员工ID（可选）</label>
            <input id="rc-daily-emp" class="input" type="number" placeholder="0=全部">
          </div>
          <div class="form-group" style="display:flex;align-items:flex-end">
            <button class="btn btn-primary" id="btn-rc-daily-reload">查询</button>
          </div>
        </div>
      </div>
      <div id="rc-daily-result">${renderReportData('日报汇总', data)}</div>
    `;
    document.getElementById('btn-rc-daily-reload').onclick = async () => {
      const date = document.getElementById('rc-daily-date').value;
      const empId = document.getElementById('rc-daily-emp').value;
      const params = new URLSearchParams();
      if (date) params.set('date', date);
      if (empId) params.set('employee_id', empId);
      const qs = params.toString();
      const newData = await API.get(`/api/reports/daily${qs ? '?' + qs : ''}`);
      document.getElementById('rc-daily-result').innerHTML = renderReportData('日报汇总', newData);
    };
  }

  async function loadWeekly(container) {
    const data = await API.get('/api/reports/weekly');
    container.innerHTML = renderReportData('周报汇总', data);
  }

  async function loadPsych(container) {
    const data = await API.get('/api/reports/psych-weekly');
    container.innerHTML = renderReportData('学生心理健康周报', data);
  }

  async function loadComplaint(container) {
    const data = await API.get('/api/reports/complaint-weekly');
    container.innerHTML = renderReportData('投诉处理周报', data);
  }

  function renderStatCards(data) {
    if (!data || (!data.total_leads && !data.lead_count && !data.customers)) {
      return '<div class="page-placeholder"><div class="placeholder-icon">📊</div><h3>暂无仪表盘数据</h3></div>';
    }
    // 兼容多种返回格式
    const leads = data.total_leads || data.lead_count || (data.customers ? data.customers.total : 0) || '0';
    const reports = data.today_reports || data.report_count || (data.daily_reports ? data.daily_reports.today : 0) || '0';
    const pending = data.pending_approvals || data.pending_count || (data.feedback ? data.feedback.pending : 0) || '0';
    const psychHigh = (data.psych_alerts ? data.psych_alerts.high : 0) || '0';
    const psychMed = (data.psych_alerts ? data.psych_alerts.medium : 0) || '0';

    let html = `<div class="stats-grid mb-16">
      <div class="stat-card stat-card--blue"><div class="stat-card__icon">👥</div><div class="stat-card__value">${leads}</div><div class="stat-card__label">意向客户总数</div></div>
      <div class="stat-card stat-card--green"><div class="stat-card__icon">📝</div><div class="stat-card__value">${reports}</div><div class="stat-card__label">今日日报数</div></div>
      <div class="stat-card stat-card--orange"><div class="stat-card__icon">✅</div><div class="stat-card__value">${pending}</div><div class="stat-card__label">待处理反馈</div></div>
      <div class="stat-card stat-card--red"><div class="stat-card__icon">🧠</div><div class="stat-card__value">${psychHigh}</div><div class="stat-card__label">高风险预警</div></div>
    </div>`;
    // 如果有客户分状态数据
    if (data.customers && data.customers.by_status) {
      html += '<div class="card"><h4 style="margin-bottom:12px">客户状态分布</h4><div class="stats-grid">';
      for (const [status, count] of Object.entries(data.customers.by_status)) {
        html += `<div class="stat-card stat-card--blue"><div class="stat-card__value">${count}</div><div class="stat-card__label">${esc(status)}</div></div>`;
      }
      html += '</div></div>';
    }
    // 显示原始 JSON（折叠）
    html += renderJsonDump(data);
    return html;
  }

  function renderReportData(title, data) {
    if (!data) {
      return '<div class="page-placeholder"><div class="placeholder-icon">📊</div><h3>暂无数据</h3></div>';
    }
    let html = `<div class="card"><h4 style="margin-bottom:12px">${title}</h4>`;
    // 遍历所有字段展示
    html += '<div class="info-grid">';
    for (const [key, value] of Object.entries(data)) {
      if (value === null || value === undefined) continue;
      if (typeof value === 'object') {
        html += `<div class="info-item" style="grid-column:span 2"><span class="info-item__label">${formatKey(key)}</span><pre style="font-size:12px;white-space:pre-wrap;margin-top:4px">${esc(JSON.stringify(value, null, 2))}</pre></div>`;
      } else {
        html += infoRow(formatKey(key), String(value));
      }
    }
    html += '</div>';

    // 如有 results / items 数组数据，尝试渲染表格
    const items = data.results || data.items || data.data;
    if (items && Array.isArray(items) && items.length) {
      const columns = Object.keys(items[0]);
      html += `
        <div class="table-container mt-16">
          <table class="table">
            <thead><tr>${columns.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>
            <tbody>
              ${items.map(row => `
                <tr>${columns.map(c => `<td>${esc(String(row[c] ?? '-'))}</td>`).join('')}</tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    }
    html += '</div>';
    return html;
  }

  function renderJsonDump(data) {
    return `
      <details class="card mt-16" style="cursor:pointer">
        <summary style="font-weight:600;font-size:13px;color:var(--color-text-secondary);padding:8px 0">查看原始数据</summary>
        <pre style="font-size:11px;white-space:pre-wrap;max-height:400px;overflow-y:auto;background:var(--color-bg);padding:12px;border-radius:6px;margin-top:8px">${esc(JSON.stringify(data, null, 2))}</pre>
      </details>
    `;
  }

  function infoRow(label, value) {
    return `<div class="info-item"><span class="info-item__label">${label}</span><span class="info-item__value">${esc(value)}</span></div>`;
  }

  function formatKey(key) {
    const map = {
      total_leads: '客户总数', lead_count: '客户总数', today_reports: '今日日报', report_count: '日报数',
      pending_approvals: '待审批', pending_count: '待处理', active_events: '进行中活动',
      psych_alerts: '心理预警', daily_reports: '日报统计', by_status: '按状态分布',
      total: '总计', pending: '待处理', high: '高风险', medium: '中风险',
    };
    return map[key] || key.replace(/_/g, ' ');
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
