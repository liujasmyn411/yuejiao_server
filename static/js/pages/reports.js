/**
 * 员工日报页 — 提交 + 列表查询
 */
const ReportsPage = (() => {
  let currentEmpId = 0;

  function render() {
    return `
      <div class="page-header flex-between">
        <h3 style="margin:0">📝 员工日报</h3>
        <div class="flex-center gap-8">
          <button class="btn" id="btn-voice-report">🎙 语音转日报</button>
          <button class="btn btn-primary" id="btn-new-report">+ 写日报</button>
        </div>
      </div>
      <div id="reports-table" class="table-container mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    document.getElementById('btn-new-report').onclick = openCreateModal;
    document.getElementById('btn-voice-report').onclick = openVoiceModal;
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
        if (!user.id) { Toast.show('登录信息失效，请重新登录', 'error'); return; }
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

  function openVoiceModal() {
    Modal.show({
      title: '语音转日报',
      body: `
        <p class="text-muted mb-16">输入口述的工作内容，AI 将自动生成结构化日报</p>
        <div class="form-group">
          <label>口述内容 <span class="text-error">*</span></label>
          <textarea id="voice-text" class="textarea" rows="6" placeholder="例如：今天上午跟进了3个意向客户，下午参加了市场部周会，整理了本周的客户数据报表..."></textarea>
        </div>
        <div id="voice-preview"></div>
      `,
      confirmText: '生成日报预览',
      autoClose: false,
      onConfirm: async () => {
        const text = document.getElementById('voice-text').value.trim();
        if (!text) { Toast.show('请输入口述内容', 'warning'); return; }
        const preview = document.getElementById('voice-preview');
        preview.innerHTML = '<div class="page-loading">AI 解析中...</div>';
        try {
          const data = await API.post('/api/enterprise/voice-report', { message: text });
          if (data.success && data.report) {
            const r = data.report;
            preview.innerHTML = `
              <div class="card mt-16" style="border:2px solid var(--color-success)">
                <h4 style="margin-bottom:12px;color:var(--color-success)">AI 解析结果</h4>
                <div class="info-grid">
                  <div class="info-item"><span class="info-item__label">日期</span><span class="info-item__value">${esc(r.report_date || '-')}</span></div>
                  <div class="info-item"><span class="info-item__label">工作类型</span><span class="info-item__value">${esc(r.work_type || '-')}</span></div>
                  <div class="info-item" style="grid-column:span 2"><span class="info-item__label">摘要</span><span class="info-item__value">${esc(r.summary || '-')}</span></div>
                  <div class="info-item" style="grid-column:span 2"><span class="info-item__label">待办事项</span><span class="info-item__value">${esc(r.todos || '-')}</span></div>
                </div>
                <button class="btn btn-primary mt-16" id="btn-submit-voice">确认提交日报</button>
              </div>
            `;
            document.getElementById('btn-submit-voice').onclick = async () => {
              const user = JSON.parse(localStorage.getItem('user') || '{}');
              if (!user.id) {
                Toast.show('登录信息失效，请重新登录', 'error');
                return;
              }
              // 规范化日期，防止 LLM 返回 "今天" 等非标准格式
              let reportDate = r.report_date;
              if (!reportDate || !/^\d{4}-\d{2}-\d{2}$/.test(reportDate)) {
                reportDate = new Date().toISOString().slice(0, 10);
              }
              // 强制转换为字符串，防止 LLM 返回数组导致 422
              const summaryStr = r.summary ? String(r.summary) : '';
              const todosStr = Array.isArray(r.todos) ? r.todos.filter(Boolean).join('；') : (r.todos ? String(r.todos) : '');
              const content = [summaryStr, todosStr].filter(Boolean).join('\n待办：');
              if (!content.trim()) {
                Toast.show('日报内容为空，无法提交', 'warning');
                return;
              }
              const workTypeStr = Array.isArray(r.work_type)
                ? r.work_type.filter(Boolean).join(',').slice(0, 50)
                : String(r.work_type || '其他').slice(0, 50);
              try {
                await API.post('/api/enterprise/report', {
                  employee_id: user.id,
                  report_date: reportDate,
                  work_type: workTypeStr,
                  content: content,
                });
                Toast.show('日报提交成功', 'success');
                Modal.hide();
                load();
              } catch (e) {
                Toast.show('提交失败: ' + e.message, 'error');
              }
            };
          } else {
            preview.innerHTML = '<div class="page-error">AI 解析失败，请重试</div>';
          }
        } catch (e) {
          preview.innerHTML = `<div class="page-error">解析失败: ${e.message}</div>`;
        }
      },
    });
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
