/**
 * 审批管理页 — 班主任查看待审批请假 + 通过/驳回
 */
const ApprovalsPage = (() => {
  function render() {
    return `
      <div class="page-header"><h3 style="margin:0">✅ 审批管理</h3></div>
      <div id="approvals-table" class="mt-16">
        <div class="page-loading">加载中...</div>
      </div>
    `;
  }

  async function onMount() {
    await load();
  }

  async function load() {
    const container = document.getElementById('approvals-table');
    try {
      const data = await API.get('/api/enterprise/approvals/pending');
      const pending = data.pending || [];
      if (!pending.length) {
        container.innerHTML = '<div class="page-placeholder"><div class="placeholder-icon">✅</div><h3>暂无待审批事项</h3></div>';
        return;
      }
      container.innerHTML = `
        <div class="card mb-16">
          <span class="text-muted">共 <strong>${data.count}</strong> 条待审批</span>
        </div>
        <div class="table-container">
          <table class="table">
            <thead><tr><th>申请ID</th><th>学生</th><th>类型</th><th>时间</th><th>原因</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              ${pending.map(p => `
                <tr>
                  <td>${p.id}</td>
                  <td><strong>${esc(p.student_name || '学生#' + p.student_id)}</strong></td>
                  <td>${esc(p.leave_type || p.service_type || '-')}</td>
                  <td>${esc((p.start_time || '').slice(0,16))} ~ ${esc((p.end_time || '').slice(0,16))}</td>
                  <td style="max-width:200px">${esc(p.reason || '-')}</td>
                  <td><span class="tag tag-orange">${esc(p.status)}</span></td>
                  <td>
                    <button class="btn btn-sm btn-success btn-approve" data-id="${p.id}">通过</button>
                    <button class="btn btn-sm btn-danger btn-reject" data-id="${p.id}">驳回</button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;

      container.querySelectorAll('.btn-approve').forEach(btn => {
        btn.onclick = () => handleApprove(btn.dataset.id, true);
      });
      container.querySelectorAll('.btn-reject').forEach(btn => {
        btn.onclick = () => handleApprove(btn.dataset.id, false);
      });
    } catch (e) {
      container.innerHTML = `<div class="page-error">加载失败: ${e.message}</div>`;
    }
  }

  function handleApprove(id, approved) {
    if (!approved) {
      Modal.show({
        title: '驳回申请',
        body: `<div class="form-group"><label>驳回原因</label><textarea id="reject-reason" class="textarea" rows="3" placeholder="请填写驳回原因"></textarea></div>`,
        confirmText: '确认驳回',
        onConfirm: async () => {
          const reason = document.getElementById('reject-reason').value.trim();
          if (!reason) { Toast.show('请填写驳回原因', 'warning'); return; }
          await submit(id, false, reason);
        },
      });
      return;
    }
    Modal.show({
      title: '确认审批',
      body: '<p>确认通过该请假申请？</p>',
      confirmText: '确认通过',
      onConfirm: () => submit(id, true),
    });
  }

  async function submit(id, approved, rejectReason) {
    try {
      await API.post(`/api/enterprise/approvals/${id}/approve`, {
        approved, reject_reason: rejectReason || null,
      });
      Toast.show(approved ? '已通过' : '已驳回', 'success');
      load();
    } catch (e) { Toast.show(e.message, 'error'); }
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

  return { render, onMount };
})();
