/**
 * 请假申请页 — 提交申请 + 历史记录
 */
const LeavePage = (() => {
  function render() {
    return `
      <div class="page-header flex-between">
        <h3 style="margin:0">🏖 请假申请</h3>
        <button class="btn btn-primary" id="btn-new-leave">+ 提交申请</button>
      </div>
      <div id="leave-list" class="mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    document.getElementById('btn-new-leave').onclick = () => openCreateModal(user.id);
    load(user.id);
  }

  async function load(studentId) {
    const container = document.getElementById('leave-list');
    try {
      const data = await API.get(`/api/student/leave?student_id=${studentId}`);
      const leaves = data.leaves || [];
      if (!leaves.length) {
        container.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">🏖</div><h3>暂无请假记录</h3><p>点击右上角提交申请</p></div>';
        return;
      }
      container.innerHTML = `
        <div class="table-container">
          <table class="table">
            <thead><tr><th>ID</th><th>类型</th><th>开始</th><th>结束</th><th>原因</th><th>状态</th><th>驳回原因</th></tr></thead>
            <tbody>
              ${leaves.map(l => `
                <tr>
                  <td>${l.id}</td>
                  <td>${esc(l.leave_type || '-')}</td>
                  <td>${esc(l.start)}</td>
                  <td>${esc(l.end)}</td>
                  <td>${esc(l.reason || '-')}</td>
                  <td>${statusTag(l.status)}</td>
                  <td>${esc(l.reject_reason || '-')}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function openCreateModal(studentId) {
    Modal.show({
      title: '提交请假申请',
      body: `
        <div class="form-grid">
          <div class="form-group">
            <label>请假类型 <span class="text-error">*</span></label>
            <select id="lv-type" class="select">
              <option value="">请选择</option><option>病假</option><option>事假</option>
            </select>
          </div>
          <div class="form-group">
            <label>开始时间 <span class="text-error">*</span></label>
            <input id="lv-start" class="input" type="datetime-local">
          </div>
          <div class="form-group">
            <label>结束时间 <span class="text-error">*</span></label>
            <input id="lv-end" class="input" type="datetime-local">
          </div>
          <div class="form-group" style="grid-column:span 2">
            <label>请假原因</label>
            <textarea id="lv-reason" class="textarea" rows="3"></textarea>
          </div>
        </div>
      `,
      confirmText: '提交',
      onConfirm: async () => {
        const get = (id) => document.getElementById(id).value;
        const leaveType = get('lv-type');
        const start = get('lv-start');
        const end = get('lv-end');
        if (!leaveType || !start || !end) { Toast.show('请填写必填字段', 'warning'); return; }
        try {
          await API.post('/api/student/leave', {
            student_id: studentId,
            service_type: '请假',
            leave_type: leaveType,
            start_time: start.replace('T', ' ') + ':00',
            end_time: end.replace('T', ' ') + ':00',
            reason: get('lv-reason'),
          });
          Toast.show('请假申请已提交', 'success');
          load(studentId);
        } catch (e) { Toast.show(e.message, 'error'); }
      },
    });
  }

  function statusTag(s) {
    const map = { '待审批': 'tag-orange', '已通过': 'tag-green', '已驳回': 'tag-red' };
    return `<span class="tag ${map[s] || 'tag-blue'}">${esc(s)}</span>`;
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
