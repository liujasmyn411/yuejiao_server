/**
 * 员工日报页 — 提交 + 列表查询
 */
const ReportsPage = (() => {
  let currentEmpId = 0;

  function render() {
    return `
      <div class="page-header flex-between">
        <h3 style="margin:0">📝 员工日报</h3>
        <button class="btn btn-primary" id="btn-new-report">+ 写日报</button>
      </div>
      <div id="reports-table" class="table-container mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    document.getElementById('btn-new-report').onclick = openCreateModal;
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    currentEmpId = user.id;
    load();
  }

  async function load() {
    const container = document.getElementById('reports-table');
    try {
      const url = currentEmpId ? `/api/enterprise/report?employee_id=${currentEmpId}` : '/api/enterprise/report';
      const data = await API.get(url);
      const reports = data.reports || [];
      if (!reports.length) {
        container.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">📝</div><h3>暂无日报</h3><p>点击右上角"写日报"开始</p></div>';
        return;
      }
      container.innerHTML = `
        <table class="table">
          <thead><tr><th>ID</th><th>员工ID</th><th>日期</th><th>类型</th><th>内容</th><th>AI摘要</th><th>状态</th></tr></thead>
          <tbody>
            ${reports.map(r => `
              <tr>
                <td>${r.id}</td>
                <td>${r.employee_id}</td>
                <td>${r.report_date}</td>
                <td>${esc(r.work_type || '-')}</td>
                <td style="max-width:300px;white-space:pre-wrap">${esc(r.content)}</td>
                <td style="max-width:200px">${esc(r.summary || '-')}</td>
                <td>${statusTag(r.report_status)}</td>
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
    const today = new Date().toISOString().slice(0, 10);
    Modal.show({
      title: '写日报',
      body: `
        <div class="form-group">
          <label>日期</label>
          <input id="rpt-date" class="input" type="date" value="${today}">
        </div>
        <div class="form-group">
          <label>工作类型</label>
          <select id="rpt-type" class="select">
            <option value="">请选择</option>
            <option>客户跟进</option><option>活动策划</option><option>项目推广</option>
            <option>内部培训</option><option>数据分析</option><option>其他</option>
          </select>
        </div>
        <div class="form-group">
          <label>日报内容 <span class="text-error">*</span></label>
          <textarea id="rpt-content" class="textarea" rows="6" placeholder="今天做了什么..."></textarea>
        </div>
      `,
      confirmText: '提交',
      onConfirm: async () => {
        const content = document.getElementById('rpt-content').value.trim();
        if (!content) { Toast.show('请输入日报内容', 'warning'); return; }
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        try {
          await API.post('/api/enterprise/report', {
            employee_id: user.id,
            report_date: document.getElementById('rpt-date').value,
            work_type: document.getElementById('rpt-type').value,
            content: content,
          });
          Toast.show('日报提交成功', 'success');
          load();
        } catch (e) { Toast.show(e.message, 'error'); }
      },
    });
  }

  function statusTag(s) {
    const map = { '已提交': 'tag-green', '草稿': 'tag-orange' };
    return `<span class="tag ${map[s] || 'tag-blue'}">${esc(s)}</span>`;
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
