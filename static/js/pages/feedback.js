/**
 * 反馈工单页 — 提交 + 列表 + 处理
 */
const FeedbackPage = (() => {
  function render() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const isStudent = user.user_type === 'STUDENT';
    return `
      <div class="page-header flex-between">
        <h3 style="margin:0">💬 反馈工单</h3>
        ${isStudent ? '<button class="btn btn-primary" id="btn-new-feedback">+ 提交反馈</button>' : ''}
      </div>
      <div id="feedback-list" class="mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const btn = document.getElementById('btn-new-feedback');
    if (btn) btn.onclick = () => openCreateModal(user.id);
    load(user);
  }

  async function load(user) {
    const container = document.getElementById('feedback-list');
    const isEmployee = user.user_type === 'EMPLOYEE' || user.user_type === 'ADMIN';
    try {
      const url = user.user_type === 'STUDENT'
        ? `/api/student/feedback?student_id=${user.id}`
        : '/api/student/feedback';
      const data = await API.get(url);
      const tickets = data.tickets || [];
      if (!tickets.length) {
        container.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">💬</div><h3>暂无反馈工单</h3></div>';
        return;
      }
      container.innerHTML = `
        <div class="table-container">
          <table class="table">
            <thead><tr><th>ID</th><th>学生ID</th><th>类型</th><th>内容</th><th>紧急度</th><th>状态</th><th>解决方案</th>${isEmployee ? '<th>操作</th>' : ''}</tr></thead>
            <tbody>
              ${tickets.map(t => `
                <tr>
                  <td>${t.id}</td>
                  <td>${t.student_id}</td>
                  <td><span class="tag tag-blue">${esc(t.feedback_type)}</span></td>
                  <td>${esc(t.content)}</td>
                  <td>${urgencyTag(t.urgency_level)}</td>
                  <td>${statusTag(t.status)}</td>
                  <td style="max-width:150px">${esc(t.solution || '-')}</td>
                  ${isEmployee ? `<td>${t.status !== '已解决' ? `<button class="btn btn-sm btn-success btn-resolve" data-id="${t.id}">解决</button>` : ''}</td>` : ''}
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
      container.querySelectorAll('.btn-resolve').forEach(btn => {
        btn.onclick = () => resolveTicket(btn.dataset.id);
      });
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function openCreateModal(studentId) {
    Modal.show({
      title: '提交反馈',
      body: `
        <div class="form-group"><label>反馈类型</label>
          <select id="fb-type" class="select"><option>咨询</option><option>投诉</option><option>建议</option></select>
        </div>
        <div class="form-group"><label>紧急程度</label>
          <select id="fb-urgent" class="select"><option>低</option><option selected>中</option><option>高</option></select>
        </div>
        <div class="form-group"><label>内容 <span class="text-error">*</span></label>
          <textarea id="fb-content" class="textarea" rows="2" placeholder="简要描述"></textarea>
        </div>
        <div class="form-group"><label>详情</label>
          <textarea id="fb-detail" class="textarea" rows="3" placeholder="详细说明"></textarea>
        </div>
      `,
      confirmText: '提交',
      onConfirm: async () => {
        const content = document.getElementById('fb-content').value.trim();
        if (!content) { Toast.show('请输入内容', 'warning'); return; }
        try {
          await API.post('/api/student/feedback', {
            student_id: studentId,
            content,
            detail: document.getElementById('fb-detail').value,
            feedback_type: document.getElementById('fb-type').value,
            urgency_level: document.getElementById('fb-urgent').value,
          });
          Toast.show('反馈已提交', 'success');
          load(JSON.parse(localStorage.getItem('user') || '{}'));
        } catch (e) { Toast.show(e.message, 'error'); }
      },
    });
  }

  function resolveTicket(id) {
    Modal.show({
      title: '处理工单',
      body: `<div class="form-group"><label>解决方案 <span class="text-error">*</span></label><textarea id="resolve-solution" class="textarea" rows="3"></textarea></div>`,
      confirmText: '标记已解决',
      onConfirm: async () => {
        const solution = document.getElementById('resolve-solution').value.trim();
        if (!solution) { Toast.show('请输入解决方案', 'warning'); return; }
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        try {
          await API.put(`/api/student/feedback/${id}/resolve`, { solution, handle_user_id: user.id });
          Toast.show('工单已处理', 'success');
          load(user);
        } catch (e) { Toast.show(e.message, 'error'); }
      },
    });
  }

  function statusTag(s) {
    const map = { '待处理': 'tag-orange', '处理中': 'tag-blue', '已解决': 'tag-green' };
    return `<span class="tag ${map[s] || 'tag-blue'}">${esc(s)}</span>`;
  }

  function urgencyTag(s) {
    const map = { '高': 'tag-red', '中': 'tag-orange', '低': 'tag-blue' };
    return `<span class="tag ${map[s] || ''}">${esc(s)}</span>`;
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
